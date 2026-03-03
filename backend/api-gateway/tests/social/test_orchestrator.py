from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from app.models import AuditEvent, FarmerReference, JlgLinkage, LoanApplication, RiskAssessment, TrustNetwork
from app.services.assessment_orchestrator import AssessmentOrchestrator
from app.services.social.models import (
    ReferenceVerificationResult,
    ReferenceVerificationStatus,
    SocialAssessmentResult,
    SocialStatus,
)


class _FakeQuery:
    def __init__(self, items: list[FarmerReference]) -> None:
        self._items = items

    def filter(self, *_args: object, **_kwargs: object) -> "_FakeQuery":
        return self

    def order_by(self, *_args: object, **_kwargs: object) -> "_FakeQuery":
        return self

    def all(self) -> list[FarmerReference]:
        return self._items


class _FakeDB:
    def __init__(self, references: list[FarmerReference]) -> None:
        self.references = references
        self.trust_rows: list[TrustNetwork] = []
        self.jlg_rows: list[JlgLinkage] = []
        self.items: list[object] = []

    def add(self, obj: object) -> None:
        self.items.append(obj)
        if isinstance(obj, TrustNetwork):
            self.trust_rows.append(obj)
        if isinstance(obj, JlgLinkage):
            self.jlg_rows.append(obj)

    def query(self, model: object) -> _FakeQuery:
        if model is FarmerReference:
            return _FakeQuery(self.references)
        if model is TrustNetwork:
            return _FakeQuery(self.trust_rows)  # type: ignore[arg-type]
        if model is JlgLinkage:
            return _FakeQuery(self.jlg_rows)  # type: ignore[arg-type]
        return _FakeQuery([])  # type: ignore[arg-type]


class _StubSocialClient:
    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        _ = farmer_mobile, reference_mobiles
        return SocialAssessmentResult(
            social_status=SocialStatus.partial,
            social_score=54,
            verified_references=1,
            reference_verifications=[
                ReferenceVerificationResult(
                    reference_mobile="+919111111112",
                    status=ReferenceVerificationStatus.verified,
                ),
                ReferenceVerificationResult(
                    reference_mobile="+919222222229",
                    status=ReferenceVerificationStatus.pending,
                ),
            ],
            provider_status="stubbed_social",
            flags=["verified_references:1", "manual_review_required"],
        )


def test_run_social_assessment_persists_social_fields_and_audit() -> None:
    app_id = uuid.uuid4()
    application = LoanApplication(
        application_id=app_id,
        banker_id="BANKER-1",
        farmer_mobile="+919999999990",
        loan_amount=30000,
        latitude=28.6139,
        longitude=77.2090,
        status="processing",
    )
    assessment = RiskAssessment(application_id=app_id)
    references = [
        FarmerReference(
            reference_id=uuid.uuid4(),
            application_id=app_id,
            farmer_mobile=application.farmer_mobile,
            reference_mobile="+919111111112",
            verification_status="pending",
            created_at=datetime.now(timezone.utc),
        ),
        FarmerReference(
            reference_id=uuid.uuid4(),
            application_id=app_id,
            farmer_mobile=application.farmer_mobile,
            reference_mobile="+919222222229",
            verification_status="pending",
            created_at=datetime.now(timezone.utc),
        ),
    ]
    db = _FakeDB(references)
    orchestrator = AssessmentOrchestrator(
        extractor=SimpleNamespace(),
        debt_client=SimpleNamespace(),
        social_client=_StubSocialClient(),
    )

    orchestrator.run_social_assessment(db=db, application=application, assessment=assessment)

    assert assessment.social_status == SocialStatus.partial.value
    assert assessment.social_provider_status == "stubbed_social"
    assert assessment.social_score == 53
    assert assessment.social_verified_references == 1
    assert assessment.social_computed_at is not None
    assert "manual_review_required" in (assessment.social_flags or [])
    assert "trust_score:52" in (assessment.social_flags or [])
    assert references[0].verification_status == "verified"
    assert references[1].verification_status == "pending"
    assert len(db.trust_rows) == 1
    assert db.trust_rows[0].trust_score == 52
    assert len(db.jlg_rows) == 2
    assert db.jlg_rows[0].linkage_status in {"active", "pending"}
    assert db.jlg_rows[1].linkage_status in {"active", "pending"}
    assert any(
        isinstance(item, AuditEvent) and item.event_type == "social_assessment_completed"
        for item in db.items
    )
