from __future__ import annotations

from time import sleep

import pytest

from app.services.social.client import SocialTrustClient
from app.services.social.exceptions import SocialProviderUnavailableError
from app.services.social.models import SocialAssessmentResult, SocialStatus


class _SlowAdapter:
    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        _ = farmer_mobile, reference_mobiles
        sleep(0.05)
        return SocialAssessmentResult(
            social_status=SocialStatus.verified,
            social_score=80,
            verified_references=2,
        )


class _UnavailableAdapter:
    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        _ = farmer_mobile, reference_mobiles
        raise SocialProviderUnavailableError("social_assess")


def test_social_timeout_maps_to_provider_unavailable_status(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.social import client as social_client_module

    monkeypatch.setattr(social_client_module.settings, "social_retry_attempts", 1)
    monkeypatch.setattr(social_client_module.settings, "social_request_timeout_seconds", 0.001)
    monkeypatch.setattr(social_client_module.settings, "social_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(social_client_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    client = SocialTrustClient(adapter=_SlowAdapter())
    result = client.assess(
        farmer_mobile="+919999999990",
        reference_mobiles=["+919111111112", "+919222222226"],
    )

    assert result.social_status == SocialStatus.provider_unavailable
    assert result.social_score is None
    assert result.provider_status == "timeout"
    assert "social_error_code:SOCIAL_PROVIDER_TIMEOUT" in result.flags


def test_social_provider_unavailable_maps_to_degraded_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.social import client as social_client_module

    monkeypatch.setattr(social_client_module.settings, "social_retry_attempts", 1)
    monkeypatch.setattr(social_client_module.settings, "social_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(social_client_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    client = SocialTrustClient(adapter=_UnavailableAdapter())
    result = client.assess(
        farmer_mobile="+919999999990",
        reference_mobiles=["+919111111112", "+919222222226"],
    )

    assert result.social_status == SocialStatus.provider_unavailable
    assert result.provider_status == "provider_unavailable"
    assert "social_error_code:SOCIAL_PROVIDER_UNAVAILABLE" in result.flags


def test_social_circuit_open_maps_to_degraded_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.social import client as social_client_module

    monkeypatch.setattr(social_client_module.settings, "social_retry_attempts", 1)
    monkeypatch.setattr(social_client_module.settings, "social_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(social_client_module.settings, "social_circuit_breaker_failure_threshold", 1)
    monkeypatch.setattr(social_client_module.settings, "social_circuit_breaker_reset_seconds", 60)
    monkeypatch.setattr(social_client_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    client = SocialTrustClient(adapter=_UnavailableAdapter())

    first = client.assess(
        farmer_mobile="+919999999990",
        reference_mobiles=["+919111111112", "+919222222226"],
    )
    second = client.assess(
        farmer_mobile="+919999999990",
        reference_mobiles=["+919111111112", "+919222222226"],
    )

    assert first.social_status == SocialStatus.provider_unavailable
    assert first.provider_status == "provider_unavailable"
    assert second.social_status == SocialStatus.provider_unavailable
    assert second.provider_status == "circuit_open"
    assert "social_error_code:SOCIAL_PROVIDER_CIRCUIT_OPEN" in second.flags

