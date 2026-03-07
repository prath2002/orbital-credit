from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.audit import emit_audit_event
from app.core.logging import log_event
from app.core.metrics import metrics_registry
from app.models import FarmerReference, JlgLinkage, LoanApplication, RiskAssessment, TrustNetwork
from app.services.debt.client import DebtServiceClient
from app.services.debt.models import DebtConsentState
from app.services.social.client import SocialTrustClient
from app.services.social.models import ReferenceVerificationStatus, SocialStatus
from app.services.satellite.feature_extractor import SatelliteFeatureExtractor


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _social_trust_delta(
    *,
    social_status: SocialStatus,
    verified_references: int,
) -> int:
    if social_status == SocialStatus.verified and verified_references == 2:
        return 8
    if social_status == SocialStatus.partial and verified_references == 1:
        return 2
    if social_status == SocialStatus.unverified:
        return -6
    if social_status == SocialStatus.provider_unavailable:
        return -2
    return 0


def _jlg_status_from_reference_status(status: ReferenceVerificationStatus) -> str:
    if status == ReferenceVerificationStatus.verified:
        return "active"
    if status == ReferenceVerificationStatus.failed:
        return "inactive"
    return "pending"


def _compute_satellite_score(
    *,
    ndvi_score: int,
    volatility: float,
    fire_detected: bool,
    fire_signal_score: float,
    data_quality: float,
) -> int:
    score = float(ndvi_score)
    score -= min(25.0, volatility * 25.0)
    score -= min(30.0, fire_signal_score * 30.0)
    if fire_detected:
        score = min(score, 20.0)
    if data_quality < 0.8:
        score -= min(20.0, (0.8 - data_quality) * 100.0 * 0.2)
    return _clamp_score(round(score))


class AssessmentOrchestrator:
    def __init__(
        self,
        extractor: SatelliteFeatureExtractor | None = None,
        debt_client: DebtServiceClient | None = None,
        social_client: SocialTrustClient | None = None,
    ) -> None:
        self.extractor = extractor or SatelliteFeatureExtractor()
        self.debt_client = debt_client or DebtServiceClient()
        self.social_client = social_client or SocialTrustClient()

    def run_satellite_assessment(
        self,
        *,
        db: Session,
        application: LoanApplication,
        assessment: RiskAssessment,
    ) -> None:
        try:
            features = self.extractor.extract(
                latitude=application.latitude,
                longitude=application.longitude,
            )
            satellite_score = _compute_satellite_score(
                ndvi_score=features.ndvi_score,
                volatility=features.volatility,
                fire_detected=features.fire_detected,
                fire_signal_score=features.fire_signal_score,
                data_quality=features.data_quality,
            )
            flags = list(features.data_quality_flags)
            flags.append(f"crop_cycle:{features.crop_cycle}")
            if features.fire_detected:
                flags.append("fire_detected")
            if features.provider_degraded:
                flags.append("provider_degraded")
            flags = sorted(set(flags))

            assessment.satellite_score = satellite_score
            assessment.satellite_quality = features.data_quality
            assessment.satellite_flags = flags
            assessment.satellite_provider_status = (
                "degraded" if features.provider_degraded else "available"
            )
            assessment.satellite_computed_at = datetime.now(timezone.utc)
            if features.data_quality < 0.8:
                metrics_registry.increment_data_quality_low()

            emit_audit_event(
                db=db,
                event="satellite_assessment_completed",
                actor_type="service",
                actor_id="SATELLITE-SERVICE",
                application_id=application.application_id,
                payload={
                    "satellite_score": satellite_score,
                    "satellite_quality": features.data_quality,
                    "satellite_provider_status": assessment.satellite_provider_status,
                    "flags": flags,
                    "fire_detected": features.fire_detected,
                    "upstream_dependency": "planetary-computer",
                },
            )
            log_event(
                event="assessment_satellite_persisted",
                application_id=str(application.application_id),
                payload={
                    "satellite_score": satellite_score,
                    "satellite_quality": features.data_quality,
                    "satellite_provider_status": assessment.satellite_provider_status,
                    "flag_count": len(flags),
                },
            )
        except Exception as exc:  # pragma: no cover - provider failure path
            assessment.satellite_score = None
            assessment.satellite_quality = 0.0
            assessment.satellite_flags = [f"satellite_error:{type(exc).__name__}"]
            assessment.satellite_provider_status = "failed"
            assessment.satellite_computed_at = datetime.now(timezone.utc)
            emit_audit_event(
                db=db,
                event="satellite_assessment_failed",
                actor_type="service",
                actor_id="SATELLITE-SERVICE",
                application_id=application.application_id,
                payload={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "upstream_dependency": "planetary-computer",
                },
            )
            log_event(
                level="ERROR",
                event="assessment_satellite_failed",
                application_id=str(application.application_id),
                payload={"error_type": type(exc).__name__},
            )

    def run_debt_assessment(
        self,
        *,
        db: Session,
        application: LoanApplication,
        assessment: RiskAssessment,
    ) -> None:
        try:
            result = self.debt_client.assess(
                farmer_mobile=application.farmer_mobile,
                loan_amount=application.loan_amount,
            )
            assessment.debt_score = result.debt_score
            assessment.debt_status = result.consent_state.value
            assessment.debt_provider_status = result.provider_status
            assessment.debt_flags = sorted(set(result.flags))
            assessment.debt_existing_amount = result.existing_debt
            assessment.debt_proposed_amount = result.proposed_debt
            assessment.debt_estimated_income = result.estimated_income
            assessment.debt_to_income_ratio = result.debt_to_income_ratio
            assessment.debt_computed_at = datetime.now(timezone.utc)

            emit_audit_event(
                db=db,
                event="debt_assessment_completed",
                actor_type="service",
                actor_id="DEBT-SERVICE",
                application_id=application.application_id,
                payload={
                    "debt_status": result.consent_state.value,
                    "debt_score": result.debt_score,
                    "debt_existing_amount": result.existing_debt,
                    "debt_proposed_amount": result.proposed_debt,
                    "debt_estimated_income": result.estimated_income,
                    "debt_to_income_ratio": result.debt_to_income_ratio,
                    "debt_provider_status": result.provider_status,
                    "flags": assessment.debt_flags,
                    "upstream_dependency": "debt-provider",
                },
            )
            log_event(
                event="assessment_debt_persisted",
                application_id=str(application.application_id),
                payload={
                    "debt_status": result.consent_state.value,
                    "debt_score_present": result.debt_score is not None,
                    "debt_to_income_ratio": result.debt_to_income_ratio,
                    "debt_provider_status": result.provider_status,
                },
            )
        except Exception as exc:  # pragma: no cover - provider failure path
            assessment.debt_score = None
            assessment.debt_status = DebtConsentState.provider_unavailable.value
            assessment.debt_provider_status = "failed"
            assessment.debt_flags = [f"debt_error:{type(exc).__name__}", "manual_review_required"]
            assessment.debt_existing_amount = None
            assessment.debt_proposed_amount = None
            assessment.debt_estimated_income = None
            assessment.debt_to_income_ratio = None
            assessment.debt_computed_at = datetime.now(timezone.utc)

            emit_audit_event(
                db=db,
                event="debt_assessment_failed",
                actor_type="service",
                actor_id="DEBT-SERVICE",
                application_id=application.application_id,
                payload={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "upstream_dependency": "debt-provider",
                },
            )
            log_event(
                level="ERROR",
                event="assessment_debt_failed",
                application_id=str(application.application_id),
                payload={"error_type": type(exc).__name__},
            )

    def run_social_assessment(
        self,
        *,
        db: Session,
        application: LoanApplication,
        assessment: RiskAssessment,
    ) -> None:
        references: list[FarmerReference] = []
        try:
            all_references = db.query(FarmerReference).all()
            references = [
                row for row in all_references if row.application_id == application.application_id
            ]
            references.sort(key=lambda row: row.created_at or datetime.now(timezone.utc))
            reference_mobiles = [row.reference_mobile for row in references]

            result = self.social_client.assess(
                farmer_mobile=application.farmer_mobile,
                reference_mobiles=reference_mobiles,
            )
            verification_by_mobile = {
                item.reference_mobile: item.status.value
                for item in result.reference_verifications
            }
            for reference_row in references:
                status = verification_by_mobile.get(reference_row.reference_mobile)
                if status:
                    reference_row.verification_status = status

            all_trust_rows = db.query(TrustNetwork).all()
            trust_row = next(
                (row for row in all_trust_rows if row.farmer_mobile == application.farmer_mobile),
                None,
            )
            if trust_row is None:
                trust_row = TrustNetwork(
                    farmer_mobile=application.farmer_mobile,
                    trust_score=50,
                )
                db.add(trust_row)
            trust_before = trust_row.trust_score
            delta = _social_trust_delta(
                social_status=result.social_status,
                verified_references=result.verified_references,
            )
            trust_after = _clamp_score(trust_before + delta)
            trust_row.trust_score = trust_after
            trust_row.last_updated_at = datetime.now(timezone.utc)

            all_jlg_rows = db.query(JlgLinkage).all()
            linkage_writes = 0
            for verification in result.reference_verifications:
                existing = next(
                    (
                        row
                        for row in all_jlg_rows
                        if row.farmer_mobile == application.farmer_mobile
                        and row.reference_mobile == verification.reference_mobile
                    ),
                    None,
                )
                linkage_status = _jlg_status_from_reference_status(verification.status)
                if existing is None:
                    db.add(
                        JlgLinkage(
                            application_id=application.application_id,
                            farmer_mobile=application.farmer_mobile,
                            reference_mobile=verification.reference_mobile,
                            linkage_status=linkage_status,
                        )
                    )
                else:
                    existing.application_id = application.application_id
                    existing.linkage_status = linkage_status
                    existing.updated_at = datetime.now(timezone.utc)
                linkage_writes += 1

            blended_social_score = (
                trust_after
                if result.social_score is None
                else _clamp_score(round((0.7 * result.social_score) + (0.3 * trust_after)))
            )
            assessment.social_score = blended_social_score
            assessment.social_status = result.social_status.value
            assessment.social_provider_status = result.provider_status
            assessment.social_flags = sorted(set(result.flags + [f"trust_score:{trust_after}"]))
            assessment.social_verified_references = result.verified_references
            assessment.social_computed_at = datetime.now(timezone.utc)

            emit_audit_event(
                db=db,
                event="social_assessment_completed",
                actor_type="service",
                actor_id="SOCIAL-TRUST-SERVICE",
                application_id=application.application_id,
                payload={
                    "social_status": result.social_status.value,
                    "social_score": blended_social_score,
                    "verified_references": result.verified_references,
                    "trust_score_before": trust_before,
                    "trust_score_after": trust_after,
                    "jlg_linkage_writes": linkage_writes,
                    "reference_verification": [
                        {"reference_mobile": item.reference_mobile, "status": item.status.value}
                        for item in result.reference_verifications
                    ],
                    "social_provider_status": result.provider_status,
                    "flags": assessment.social_flags,
                    "upstream_dependency": "social-provider",
                },
            )
            log_event(
                event="assessment_social_persisted",
                application_id=str(application.application_id),
                payload={
                    "social_status": result.social_status.value,
                    "social_score_present": blended_social_score is not None,
                    "verified_references": result.verified_references,
                    "social_provider_status": result.provider_status,
                    "trust_score_after": trust_after,
                    "jlg_linkage_writes": linkage_writes,
                },
            )
        except Exception as exc:  # pragma: no cover - provider failure path
            for reference_row in references:
                reference_row.verification_status = "provider_unavailable"
            assessment.social_score = None
            assessment.social_status = SocialStatus.provider_unavailable.value
            assessment.social_provider_status = "failed"
            assessment.social_flags = [f"social_error:{type(exc).__name__}", "manual_review_required"]
            assessment.social_verified_references = 0
            assessment.social_computed_at = datetime.now(timezone.utc)

            emit_audit_event(
                db=db,
                event="social_assessment_failed",
                actor_type="service",
                actor_id="SOCIAL-TRUST-SERVICE",
                application_id=application.application_id,
                payload={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "upstream_dependency": "social-provider",
                },
            )
            log_event(
                level="ERROR",
                event="assessment_social_failed",
                application_id=str(application.application_id),
                payload={"error_type": type(exc).__name__},
            )
