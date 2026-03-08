from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models import LoanApplication, RiskAssessment
from app.schemas import (
    AgentRecommendationItem,
    AgentRecommendationResponse,
    DebtStatus,
    DecisionRequest,
    ManualAction,
)
from app.services.decision_engine import DecisionEngine


@dataclass
class AgentGraphState:
    application: LoanApplication
    assessment: RiskAssessment | None
    graph_path: list[str] = field(default_factory=list)
    zone: str | None = None
    reasons: list[str] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)
    recommendation: AgentRecommendationItem | None = None


class AgentRecommendationService:
    """LangGraph-style staged agent, grounded by deterministic decision rules."""

    def __init__(self, decision_engine: DecisionEngine | None = None) -> None:
        self.decision_engine = decision_engine or DecisionEngine()

    def _build_decision_payload(self, state: AgentGraphState) -> DecisionRequest | None:
        state.graph_path.append("load_case_context")
        assessment = state.assessment
        if assessment is None:
            return None
        if (
            assessment.satellite_score is None
            or assessment.debt_to_income_ratio is None
            or assessment.social_verified_references is None
        ):
            return None

        debt_status_raw = (assessment.debt_status or DebtStatus.unverified.value).strip().lower()
        try:
            debt_status = DebtStatus(debt_status_raw)
        except Exception:
            debt_status = DebtStatus.unverified

        return DecisionRequest(
            manual_action=ManualAction.escalate,
            satellite_score=assessment.satellite_score,
            debt_score=assessment.debt_score,
            social_score=assessment.social_score,
            satellite_data_quality=assessment.satellite_quality or 0.0,
            debt_to_income_ratio=assessment.debt_to_income_ratio,
            debt_status=debt_status,
            social_verified_references=assessment.social_verified_references,
            satellite_no_crop_history=("no_crop_history" in (assessment.satellite_flags or [])),
            satellite_fire_detected=("fire_detected" in (assessment.satellite_flags or [])),
            identity_verification_failed=False,
            rationale_override=assessment.rationale,
            actor_id="agent-orchestrator",
        )

    @staticmethod
    def _strip_reason_prefix(reason: str) -> str:
        parts = reason.split(": ", 1)
        return parts[1] if len(parts) == 2 else reason

    def _plan_required_checks(self, payload: DecisionRequest, reasons: list[str]) -> list[str]:
        checks: list[str] = []
        if payload.satellite_data_quality < 0.80:
            checks.append("Validate crop evidence using alternate satellite window or field verification.")
        if payload.debt_status in {DebtStatus.timeout, DebtStatus.provider_unavailable, DebtStatus.consent_pending}:
            checks.append("Collect banker-verified liability and income evidence before final approval.")
        if payload.social_verified_references < 2:
            checks.append("Re-run two-reference verification and capture confirmation notes.")
        if not checks:
            checks.append("Follow standard manual underwriting checklist.")
        for reason in reasons:
            if "borderline range" in reason.lower():
                checks.append("Escalate to senior underwriter due to borderline risk factors.")
                break
        return checks[:3]

    @staticmethod
    def _confidence_for_zone(zone: str, payload: DecisionRequest) -> float:
        if zone == "GREEN":
            return 0.84
        if zone == "RED":
            return 0.9
        # YELLOW: lower confidence as uncertainty grows.
        penalty = 0.0
        if payload.satellite_data_quality < 0.8:
            penalty += 0.08
        if payload.debt_status in {DebtStatus.timeout, DebtStatus.provider_unavailable, DebtStatus.consent_pending}:
            penalty += 0.07
        if payload.social_verified_references < 2:
            penalty += 0.05
        return max(0.45, min(0.75, 0.68 - penalty))

    def _fallback_recommendation(self, state: AgentGraphState) -> AgentRecommendationItem:
        state.graph_path.append("await_assessment_data")
        return AgentRecommendationItem(
            action=ManualAction.escalate,
            confidence=0.42,
            summary="Assessment data is incomplete. Manual review is required before final decision.",
            primary_reasons=["One or more risk layers are pending or incomplete."],
            required_checks=[
                "Wait for satellite, debt, and social assessments to complete.",
                "Confirm provider statuses before finalizing decision.",
            ],
            expected_impact_if_approved="Approval without complete signals may increase delinquency risk.",
            expected_impact_if_rejected="Rejection before full data may drop potentially viable borrowers.",
        )

    def run(self, *, application: LoanApplication, assessment: RiskAssessment | None) -> AgentRecommendationResponse:
        state = AgentGraphState(application=application, assessment=assessment)
        payload = self._build_decision_payload(state)

        if payload is None:
            recommendation = self._fallback_recommendation(state)
            return AgentRecommendationResponse(
                application_id=application.application_id,
                generated_at=datetime.now(timezone.utc),
                traffic_light_status=assessment.traffic_light_status if assessment else None,
                graph_path=state.graph_path,
                recommendation=recommendation,
            )

        state.graph_path.append("run_rule_grounding")
        zone, reasons = self.decision_engine.evaluate_zone(payload)
        state.zone = zone
        state.reasons = reasons

        if zone == "YELLOW":
            state.graph_path.append("plan_missing_checks")
            state.required_checks = self._plan_required_checks(payload, reasons)
        else:
            state.graph_path.append("build_direct_recommendation")
            state.required_checks = ["Proceed with standard approval workflow."] if zone == "GREEN" else ["Document rejection rationale and notify banker."]

        state.graph_path.append("synthesize_recommendation")
        action = ManualAction.approve if zone == "GREEN" else ManualAction.reject if zone == "RED" else ManualAction.escalate
        primary_reasons = [self._strip_reason_prefix(reason) for reason in reasons[:3]]
        summary = (
            "Strong signals across satellite, debt, and social layers support approval."
            if zone == "GREEN"
            else (
                "Hard-fail rule(s) triggered. Recommend rejection."
                if zone == "RED"
                else "Uncertainty remains in one or more layers. Escalate for manual review."
            )
        )
        recommendation = AgentRecommendationItem(
            action=action,
            confidence=self._confidence_for_zone(zone, payload),
            summary=summary,
            primary_reasons=primary_reasons,
            required_checks=state.required_checks,
            expected_impact_if_approved="Improves credit access but may increase exposure if hidden risks materialize.",
            expected_impact_if_rejected="Reduces portfolio risk but may decline potentially recoverable cases.",
        )
        state.recommendation = recommendation
        state.graph_path.append("persist_agent_result")

        return AgentRecommendationResponse(
            application_id=application.application_id,
            generated_at=datetime.now(timezone.utc),
            traffic_light_status=zone,
            graph_path=state.graph_path,
            recommendation=recommendation,
        )
