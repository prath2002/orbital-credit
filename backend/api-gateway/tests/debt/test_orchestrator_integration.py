from __future__ import annotations

from types import SimpleNamespace
import uuid

from app.models import AuditEvent, LoanApplication, RiskAssessment
from app.services.assessment_orchestrator import AssessmentOrchestrator
from app.services.debt.client import DebtServiceClient
from app.services.debt.exceptions import DebtTimeoutError
from app.services.debt.models import DebtAssessmentResult, DebtConsentState


class _FakeDB:
    def __init__(self) -> None:
        self.items: list[object] = []

    def add(self, obj: object) -> None:
        self.items.append(obj)


class _VerifiedAdapter:
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        _ = farmer_mobile, loan_amount
        return DebtAssessmentResult(
            consent_state=DebtConsentState.verified,
            debt_score=74,
            existing_debt=12000,
            proposed_debt=42000,
            estimated_income=100000,
            debt_to_income_ratio=0.42,
            provider_status="stubbed_success",
            flags=["consent_state:verified"],
        )


class _TimeoutAdapter:
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        _ = farmer_mobile, loan_amount
        raise DebtTimeoutError("debt_assess")


class _FailingDebtClient:
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        _ = farmer_mobile, loan_amount
        raise RuntimeError("simulated_debt_client_crash")


def _build_application_and_assessment() -> tuple[LoanApplication, RiskAssessment]:
    application = LoanApplication(
        application_id=uuid.uuid4(),
        banker_id="BANKER-1",
        farmer_mobile="+919999999990",
        loan_amount=30000,
        latitude=28.6139,
        longitude=77.2090,
        status="processing",
    )
    assessment = RiskAssessment(application_id=application.application_id)
    return application, assessment


def test_debt_orchestrator_success_with_stubbed_provider() -> None:
    app, assessment = _build_application_and_assessment()
    db = _FakeDB()
    orchestrator = AssessmentOrchestrator(
        extractor=SimpleNamespace(),
        debt_client=DebtServiceClient(adapter=_VerifiedAdapter()),
    )

    orchestrator.run_debt_assessment(db=db, application=app, assessment=assessment)

    assert assessment.debt_status == DebtConsentState.verified.value
    assert assessment.debt_provider_status == "stubbed_success"
    assert assessment.debt_score == 74
    assert assessment.debt_existing_amount == 12000
    assert assessment.debt_proposed_amount == 42000
    assert assessment.debt_estimated_income == 100000
    assert assessment.debt_to_income_ratio == 0.42
    assert assessment.debt_computed_at is not None
    assert any(isinstance(item, AuditEvent) and item.event_type == "debt_assessment_completed" for item in db.items)


def test_debt_orchestrator_timeout_degrades_with_stubbed_provider() -> None:
    app, assessment = _build_application_and_assessment()
    db = _FakeDB()
    orchestrator = AssessmentOrchestrator(
        extractor=SimpleNamespace(),
        debt_client=DebtServiceClient(adapter=_TimeoutAdapter()),
    )

    orchestrator.run_debt_assessment(db=db, application=app, assessment=assessment)

    assert assessment.debt_status == DebtConsentState.timeout.value
    assert assessment.debt_provider_status == "timeout"
    assert assessment.debt_score is None
    assert "debt_error_code:DEBT_PROVIDER_TIMEOUT" in (assessment.debt_flags or [])
    assert any(isinstance(item, AuditEvent) and item.event_type == "debt_assessment_completed" for item in db.items)


def test_debt_orchestrator_handles_unexpected_debt_client_failure() -> None:
    app, assessment = _build_application_and_assessment()
    db = _FakeDB()
    orchestrator = AssessmentOrchestrator(
        extractor=SimpleNamespace(),
        debt_client=_FailingDebtClient(),
    )

    orchestrator.run_debt_assessment(db=db, application=app, assessment=assessment)

    assert assessment.debt_status == DebtConsentState.provider_unavailable.value
    assert assessment.debt_provider_status == "failed"
    assert "debt_error:RuntimeError" in (assessment.debt_flags or [])
    assert any(isinstance(item, AuditEvent) and item.event_type == "debt_assessment_failed" for item in db.items)

