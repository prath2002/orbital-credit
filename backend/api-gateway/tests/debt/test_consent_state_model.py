from __future__ import annotations

from app.services.debt.client import DebtServiceClient, MockDebtProvider
from app.services.debt.models import DebtConsentState


def test_mock_debt_provider_returns_verified_with_score() -> None:
    client = DebtServiceClient(adapter=MockDebtProvider())

    result = client.assess(farmer_mobile="+919999999990", loan_amount=30000)

    assert result.consent_state == DebtConsentState.verified
    assert result.debt_score is not None
    assert result.existing_debt is not None
    assert result.proposed_debt == result.existing_debt + 30000
    assert result.estimated_income is not None
    assert result.debt_to_income_ratio is not None
    assert result.debt_to_income_ratio == round(result.proposed_debt / result.estimated_income, 4)
    assert result.provider_status == "mock"


def test_mock_debt_provider_returns_timeout_without_score() -> None:
    client = DebtServiceClient(adapter=MockDebtProvider())

    result = client.assess(farmer_mobile="+919999999994", loan_amount=30000)

    assert result.consent_state == DebtConsentState.timeout
    assert result.debt_score is None
    assert result.debt_to_income_ratio is None


def test_mock_debt_provider_returns_provider_unavailable_without_score() -> None:
    client = DebtServiceClient(adapter=MockDebtProvider())

    result = client.assess(farmer_mobile="+919999999995", loan_amount=30000)

    assert result.consent_state == DebtConsentState.provider_unavailable
    assert result.debt_score is None
    assert result.debt_to_income_ratio is None


def test_mock_debt_provider_returns_consent_pending_without_score() -> None:
    client = DebtServiceClient(adapter=MockDebtProvider())

    result = client.assess(farmer_mobile="+919999999999", loan_amount=30000)

    assert result.consent_state == DebtConsentState.consent_pending
    assert result.debt_score is None
    assert result.debt_to_income_ratio is None


def test_mock_debt_provider_is_deterministic_for_same_input() -> None:
    client = DebtServiceClient(adapter=MockDebtProvider())

    first = client.assess(farmer_mobile="+919876543210", loan_amount=35000)
    second = client.assess(farmer_mobile="+919876543210", loan_amount=35000)

    assert first.model_dump() == second.model_dump()
