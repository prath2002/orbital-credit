from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import emit_audit_event
from app.core.logging import log_event
from app.models import JlgLinkage, LoanApplication, TrustNetwork
from app.services.social.models import ReferencePenaltyResult, SocialDefaultPenaltyResult


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _get_or_create_trust_row(db: Session, *, mobile: str, now: datetime) -> TrustNetwork:
    rows = db.query(TrustNetwork).all()
    row = next((item for item in rows if item.farmer_mobile == mobile), None)
    if row is None:
        row = TrustNetwork(
            farmer_mobile=mobile,
            trust_score=50,
            last_updated_at=now,
        )
        db.add(row)
    return row


class SocialPenaltyService:
    def apply_default_event_penalty(
        self,
        *,
        db: Session,
        application: LoanApplication,
        actor_id: str = "SOCIAL-TRUST-SERVICE",
    ) -> SocialDefaultPenaltyResult:
        now = datetime.now(timezone.utc)
        farmer_row = _get_or_create_trust_row(
            db,
            mobile=application.farmer_mobile,
            now=now,
        )
        farmer_before = farmer_row.trust_score
        farmer_after = _clamp_score(
            farmer_before - settings.social_default_penalty_farmer_points
        )
        farmer_row.trust_score = farmer_after
        farmer_row.last_updated_at = now

        linkages = [
            row
            for row in db.query(JlgLinkage).all()
            if row.farmer_mobile == application.farmer_mobile
        ]
        impacted_references: list[ReferencePenaltyResult] = []
        for linkage in linkages:
            reference_row = _get_or_create_trust_row(
                db,
                mobile=linkage.reference_mobile,
                now=now,
            )
            ref_before = reference_row.trust_score
            ref_after = _clamp_score(
                ref_before - settings.social_default_penalty_reference_points
            )
            reference_row.trust_score = ref_after
            reference_row.last_updated_at = now
            linkage.linkage_status = "default_impacted"
            linkage.updated_at = now
            impacted_references.append(
                ReferencePenaltyResult(
                    reference_mobile=linkage.reference_mobile,
                    trust_score_before=ref_before,
                    trust_score_after=ref_after,
                )
            )

        emit_audit_event(
            db=db,
            event="social_default_penalty_applied",
            actor_type="service",
            actor_id=actor_id,
            application_id=application.application_id,
            payload={
                "farmer_mobile": application.farmer_mobile,
                "farmer_trust_before": farmer_before,
                "farmer_trust_after": farmer_after,
                "impacted_reference_count": len(impacted_references),
                "impacted_references": [item.model_dump() for item in impacted_references],
                "upstream_dependency": "social-trust-service",
            },
        )
        log_event(
            event="social_default_penalty_applied",
            application_id=str(application.application_id),
            payload={
                "farmer_trust_before": farmer_before,
                "farmer_trust_after": farmer_after,
                "impacted_reference_count": len(impacted_references),
            },
        )
        return SocialDefaultPenaltyResult(
            farmer_mobile=application.farmer_mobile,
            farmer_trust_before=farmer_before,
            farmer_trust_after=farmer_after,
            impacted_references=impacted_references,
        )

