from __future__ import annotations

from typing import Protocol

from app.services.social.models import SocialAssessmentResult


class SocialProviderAdapter(Protocol):
    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        """Return social verification outputs."""

