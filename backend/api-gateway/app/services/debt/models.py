from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DebtConsentState(str, Enum):
    verified = "verified"
    timeout = "timeout"
    provider_unavailable = "provider_unavailable"
    consent_pending = "consent_pending"


class DebtAssessmentResult(BaseModel):
    consent_state: DebtConsentState
    debt_score: int | None = Field(default=None, ge=0, le=100)
    existing_debt: int | None = Field(default=None, ge=0)
    proposed_debt: int | None = Field(default=None, ge=0)
    estimated_income: int | None = Field(default=None, ge=0)
    debt_to_income_ratio: float | None = Field(default=None, ge=0.0)
    provider_status: str = "mock"
    flags: list[str] = Field(default_factory=list)
