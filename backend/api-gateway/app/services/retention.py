from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, FarmerReference, JlgLinkage, LoanApplication, RiskAssessment


class RetentionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def purge_older_than(self, *, retention_days: int) -> dict[str, int]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))

        old_app_ids = [
            row.application_id
            for row in self.db.execute(
                select(LoanApplication).where(LoanApplication.created_at < cutoff)
            ).scalars()
        ]

        deleted_farmer_refs = 0
        deleted_risk = 0
        deleted_jlg = 0
        deleted_applications = 0
        deleted_audit = 0

        if old_app_ids:
            deleted_farmer_refs = (
                self.db.query(FarmerReference)
                .filter(FarmerReference.application_id.in_(old_app_ids))
                .delete(synchronize_session=False)
            )
            deleted_risk = (
                self.db.query(RiskAssessment)
                .filter(RiskAssessment.application_id.in_(old_app_ids))
                .delete(synchronize_session=False)
            )
            deleted_jlg = (
                self.db.query(JlgLinkage)
                .filter(JlgLinkage.application_id.in_(old_app_ids))
                .delete(synchronize_session=False)
            )
            deleted_audit = (
                self.db.query(AuditEvent)
                .filter(AuditEvent.application_id.in_(old_app_ids))
                .delete(synchronize_session=False)
            )
            deleted_applications = (
                self.db.query(LoanApplication)
                .filter(LoanApplication.application_id.in_(old_app_ids))
                .delete(synchronize_session=False)
            )

        # Also delete orphan/system audit events that are old.
        deleted_audit += (
            self.db.query(AuditEvent)
            .filter(AuditEvent.application_id.is_(None))
            .filter(AuditEvent.created_at < cutoff)
            .delete(synchronize_session=False)
        )

        self.db.commit()
        return {
            "deleted_loan_applications": deleted_applications,
            "deleted_risk_assessments": deleted_risk,
            "deleted_farmer_references": deleted_farmer_refs,
            "deleted_jlg_linkages": deleted_jlg,
            "deleted_audit_events": deleted_audit,
            "cutoff_iso": cutoff.isoformat(),
        }

