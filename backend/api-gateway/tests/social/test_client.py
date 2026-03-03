from __future__ import annotations

import pytest

from app.services.social.client import SocialTrustClient
from app.services.social.exceptions import SocialProviderUnavailableError
from app.services.social.models import (
    ReferenceVerificationStatus,
    SocialAssessmentResult,
    SocialStatus,
)


class _FailingAdapter:
    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        _ = farmer_mobile, reference_mobiles
        raise SocialProviderUnavailableError("social_assess")


def test_mock_social_client_returns_verified_for_two_verified_references() -> None:
    client = SocialTrustClient()

    result = client.assess(
        farmer_mobile="+919999999990",
        reference_mobiles=["+919111111112", "+919222222226"],
    )

    assert result.social_status == SocialStatus.verified
    assert result.verified_references == 2
    assert len(result.reference_verifications) == 2
    assert all(item.status == ReferenceVerificationStatus.verified for item in result.reference_verifications)
    assert result.social_score is not None
    assert result.provider_status == "mock"


def test_mock_social_client_marks_pending_reference() -> None:
    client = SocialTrustClient()

    result = client.assess(
        farmer_mobile="+919999999990",
        reference_mobiles=["+919111111119", "+919222222226"],
    )

    assert result.verified_references == 1
    assert any(item.status == ReferenceVerificationStatus.pending for item in result.reference_verifications)
    assert "reference_verification_pending" in result.flags


def test_social_client_maps_provider_failure_to_degraded_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.social import client as social_client_module

    monkeypatch.setattr(social_client_module.settings, "social_retry_attempts", 1)
    monkeypatch.setattr(social_client_module.settings, "social_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(social_client_module.random, "uniform", lambda *_args, **_kwargs: 0.0)

    client = SocialTrustClient(adapter=_FailingAdapter())
    result = client.assess(
        farmer_mobile="+919999999990",
        reference_mobiles=["+919111111112", "+919222222226"],
    )

    assert result.social_status == SocialStatus.provider_unavailable
    assert result.social_score is None
    assert result.reference_verifications == []
    assert result.provider_status == "provider_unavailable"
    assert "social_error_code:SOCIAL_PROVIDER_UNAVAILABLE" in result.flags
