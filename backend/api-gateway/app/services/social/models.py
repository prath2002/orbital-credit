from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SocialStatus(str, Enum):
    verified = "verified"
    partial = "partial"
    unverified = "unverified"
    provider_unavailable = "provider_unavailable"


class ReferenceVerificationStatus(str, Enum):
    verified = "verified"
    failed = "failed"
    pending = "pending"
    provider_unavailable = "provider_unavailable"


class ReferenceVerificationResult(BaseModel):
    reference_mobile: str
    status: ReferenceVerificationStatus


class SocialAssessmentResult(BaseModel):
    social_status: SocialStatus
    social_score: int | None = Field(default=None, ge=0, le=100)
    verified_references: int = Field(ge=0, le=2, default=0)
    reference_verifications: list[ReferenceVerificationResult] = Field(default_factory=list)
    provider_status: str = "mock"
    flags: list[str] = Field(default_factory=list)


class ReferencePenaltyResult(BaseModel):
    reference_mobile: str
    trust_score_before: int
    trust_score_after: int


class SocialDefaultPenaltyResult(BaseModel):
    farmer_mobile: str
    farmer_trust_before: int
    farmer_trust_after: int
    impacted_references: list[ReferencePenaltyResult] = Field(default_factory=list)
