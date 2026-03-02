from __future__ import annotations

from time import sleep

import pytest

from app.services.debt.client import DebtServiceClient
from app.services.debt.exceptions import DebtProviderUnavailableError
from app.services.debt.models import DebtAssessmentResult, DebtConsentState


class _SlowAdapter:
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        _ = farmer_mobile, loan_amount
        sleep(0.05)
        return DebtAssessmentResult(consent_state=DebtConsentState.verified, debt_score=75)


class _UnavailableAdapter:
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        _ = farmer_mobile, loan_amount
        raise DebtProviderUnavailableError("debt_assess")


def test_debt_timeout_maps_to_timeout_status(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.debt import client as debt_client_module

    monkeypatch.setattr(debt_client_module.settings, "debt_retry_attempts", 1)
    monkeypatch.setattr(debt_client_module.settings, "debt_request_timeout_seconds", 0.001)
    monkeypatch.setattr(debt_client_module.settings, "debt_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(debt_client_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    client = DebtServiceClient(adapter=_SlowAdapter())

    result = client.assess(farmer_mobile="+919999999990", loan_amount=30000)

    assert result.consent_state == DebtConsentState.timeout
    assert result.debt_score is None
    assert result.provider_status == "timeout"
    assert "debt_error_code:DEBT_PROVIDER_TIMEOUT" in result.flags


def test_provider_unavailable_maps_to_manual_review_status(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.debt import client as debt_client_module

    monkeypatch.setattr(debt_client_module.settings, "debt_retry_attempts", 1)
    monkeypatch.setattr(debt_client_module.settings, "debt_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(debt_client_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    client = DebtServiceClient(adapter=_UnavailableAdapter())
    result = client.assess(farmer_mobile="+919999999990", loan_amount=30000)

    assert result.consent_state == DebtConsentState.provider_unavailable
    assert result.provider_status == "provider_unavailable"
    assert "debt_error_code:DEBT_PROVIDER_UNAVAILABLE" in result.flags


def test_circuit_open_maps_to_provider_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.debt import client as debt_client_module

    monkeypatch.setattr(debt_client_module.settings, "debt_retry_attempts", 1)
    monkeypatch.setattr(debt_client_module.settings, "debt_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(debt_client_module.settings, "debt_circuit_breaker_failure_threshold", 1)
    monkeypatch.setattr(debt_client_module.settings, "debt_circuit_breaker_reset_seconds", 60)
    monkeypatch.setattr(debt_client_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    client = DebtServiceClient(adapter=_UnavailableAdapter())

    first = client.assess(farmer_mobile="+919999999990", loan_amount=30000)
    second = client.assess(farmer_mobile="+919999999990", loan_amount=30000)

    assert first.consent_state == DebtConsentState.provider_unavailable
    assert first.provider_status == "provider_unavailable"
    assert second.consent_state == DebtConsentState.provider_unavailable
    assert second.provider_status == "circuit_open"
    assert "debt_error_code:DEBT_PROVIDER_CIRCUIT_OPEN" in second.flags

