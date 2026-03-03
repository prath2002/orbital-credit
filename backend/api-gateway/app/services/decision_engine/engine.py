from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.core.errors import ValidationError
from app.models import RiskAssessment
from app.schemas import DebtStatus, DecisionRequest, YellowExplanationBundle


@dataclass
class ResolvedDecisionInputs:
    payload: DecisionRequest
    debt_score: int
    debt_to_income_ratio: float
    debt_status: DebtStatus
    social_score: int
    social_verified_references: int


class DecisionEngine:
    def __init__(self) -> None:
        self.rule_version = settings.decision_rule_version

    @staticmethod
    def _reason_message(reason: str) -> str:
        parts = reason.split(": ", 1)
        return parts[1] if len(parts) == 2 else reason

    @staticmethod
    def extract_rule_id(reason: str) -> str | None:
        if ":" not in reason:
            return None
        candidate = reason.split(":", 1)[0].strip()
        return candidate if candidate.startswith("R-") else None

    @staticmethod
    def compute_overall_score(
        *,
        satellite_score: int,
        debt_score: int,
        social_score: int,
    ) -> int:
        return round((0.40 * satellite_score) + (0.35 * debt_score) + (0.25 * social_score))

    @staticmethod
    def resolve_debt_inputs(
        *,
        payload: DecisionRequest,
        assessment: RiskAssessment | None,
    ) -> tuple[int, float, DebtStatus]:
        debt_score = payload.debt_score if payload.debt_score is not None else None
        debt_ratio = payload.debt_to_income_ratio if payload.debt_to_income_ratio is not None else None
        debt_status = payload.debt_status

        if assessment is not None:
            if debt_score is None:
                debt_score = assessment.debt_score
            if debt_ratio is None:
                debt_ratio = assessment.debt_to_income_ratio
            if debt_status is None and assessment.debt_status:
                try:
                    debt_status = DebtStatus(assessment.debt_status)
                except ValueError:
                    debt_status = None

        if debt_score is None or debt_ratio is None or debt_status is None:
            raise ValidationError(
                code="DEBT_INPUT_INCOMPLETE",
                message="Debt decision inputs are incomplete; ensure debt assessment has finished or provide debt fields explicitly",
                status_code=422,
                retryable=False,
            )

        if debt_status == DebtStatus.unverified:
            raise ValidationError(
                code="DEBT_STATUS_UNSUPPORTED",
                message="Debt status 'unverified' is not accepted for decision finalization",
                status_code=422,
                retryable=False,
            )

        return debt_score, debt_ratio, debt_status

    @staticmethod
    def resolve_social_inputs(
        *,
        payload: DecisionRequest,
        assessment: RiskAssessment | None,
    ) -> tuple[int, int]:
        social_score = payload.social_score if payload.social_score is not None else None
        social_verified_references = (
            payload.social_verified_references
            if payload.social_verified_references is not None
            else None
        )

        if assessment is not None:
            if social_score is None:
                social_score = assessment.social_score
            if social_verified_references is None:
                social_verified_references = assessment.social_verified_references

        if social_score is None or social_verified_references is None:
            raise ValidationError(
                code="SOCIAL_INPUT_INCOMPLETE",
                message="Social decision inputs are incomplete; ensure social assessment has finished or provide social fields explicitly",
                status_code=422,
                retryable=False,
            )

        return social_score, social_verified_references

    def resolve_inputs(
        self,
        *,
        payload: DecisionRequest,
        assessment: RiskAssessment | None,
    ) -> ResolvedDecisionInputs:
        debt_score, debt_ratio, debt_status = self.resolve_debt_inputs(
            payload=payload,
            assessment=assessment,
        )
        social_score, social_verified_references = self.resolve_social_inputs(
            payload=payload,
            assessment=assessment,
        )
        resolved_payload = payload.model_copy(
            update={
                "debt_score": debt_score,
                "debt_to_income_ratio": debt_ratio,
                "debt_status": debt_status,
                "social_score": social_score,
                "social_verified_references": social_verified_references,
            }
        )
        return ResolvedDecisionInputs(
            payload=resolved_payload,
            debt_score=debt_score,
            debt_to_income_ratio=debt_ratio,
            debt_status=debt_status,
            social_score=social_score,
            social_verified_references=social_verified_references,
        )

    @staticmethod
    def evaluate_zone(payload: DecisionRequest) -> tuple[str, list[str]]:
        # Authoritative parity with documents/decision-rules-table.md (first match wins).
        if payload.satellite_no_crop_history:
            return "RED", ["R-RED-01: No crop history detected from satellite analysis"]
        if payload.satellite_fire_detected:
            return "RED", ["R-RED-02: Fire signal detected in satellite analysis"]
        if payload.debt_to_income_ratio > 0.50:
            return "RED", ["R-RED-03: Debt-to-income ratio exceeds 0.50"]
        if payload.social_verified_references < 2:
            return "RED", ["R-RED-04: Fewer than 2 verified references"]
        if payload.identity_verification_failed:
            return "RED", ["R-RED-05: Identity verification failed"]

        if (
            payload.satellite_score >= 80
            and payload.satellite_data_quality >= 0.80
            and not payload.satellite_fire_detected
        ):
            return "GREEN", ["R-GREEN-01: Strong satellite signal and quality"]
        if (
            payload.debt_to_income_ratio <= 0.30
            and payload.debt_status == "verified"
        ):
            return "GREEN", ["R-GREEN-02: Verified low debt leverage"]
        if (
            payload.social_score >= 70
            and payload.social_verified_references == 2
        ):
            return "GREEN", ["R-GREEN-03: Strong social trust verification"]

        if payload.satellite_data_quality < 0.80:
            return "YELLOW", ["R-YELLOW-01: Satellite data quality below 0.80"]
        if payload.debt_status in {"timeout", "provider_unavailable", "consent_pending"}:
            return "YELLOW", ["R-YELLOW-02: Debt provider verification incomplete"]
        if (
            (60 <= payload.satellite_score <= 79)
            or (0.31 <= payload.debt_to_income_ratio <= 0.50)
            or (40 <= payload.social_score <= 69)
        ):
            return "YELLOW", ["R-YELLOW-03: One or more factors are in borderline range"]
        return "YELLOW", ["R-YELLOW-04: Safe default manual review path"]

    def build_yellow_explanation(
        self,
        *,
        payload: DecisionRequest,
        reasons: list[str],
    ) -> YellowExplanationBundle:
        missing_or_low_confidence_data: list[str] = []
        if payload.satellite_data_quality < 0.80:
            missing_or_low_confidence_data.append("Satellite imagery quality below confidence threshold (0.80)")
        if payload.debt_status in {DebtStatus.timeout, DebtStatus.provider_unavailable, DebtStatus.consent_pending}:
            missing_or_low_confidence_data.append("Debt verification incomplete or provider unavailable")
        if payload.social_verified_references < 2:
            missing_or_low_confidence_data.append("Reference verification coverage is incomplete")

        recommended_manual_checks: list[str] = []
        if payload.satellite_data_quality < 0.80:
            recommended_manual_checks.append("Verify latest crop evidence using alternate imagery/window")
        if payload.debt_status in {DebtStatus.timeout, DebtStatus.provider_unavailable, DebtStatus.consent_pending}:
            recommended_manual_checks.append("Collect banker-verified liabilities and income proof")
        if payload.social_score < 70 or payload.social_verified_references < 2:
            recommended_manual_checks.append("Call both references and validate repayment behavior")
        if not recommended_manual_checks:
            recommended_manual_checks.append("Perform standard manual underwriting checklist")

        return YellowExplanationBundle(
            primary_reasons=[self._reason_message(reason) for reason in reasons[:3]],
            missing_or_low_confidence_data=missing_or_low_confidence_data,
            recommended_manual_checks=recommended_manual_checks[:3],
            expected_impact_if_approved="Higher probability of delinquency if uncertain factors are adverse.",
            expected_impact_if_rejected="Potential good borrower loss if uncertainties would have resolved positively.",
        )
