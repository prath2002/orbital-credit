from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApplicationStatus(str, Enum):
    processing = "processing"
    completed = "completed"


class Coordinates(BaseModel):
    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if value < -90 or value > 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if value < -180 or value > 180:
            raise ValueError("longitude must be between -180 and 180")
        return value


class AnalyzeFarmRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    gps_coordinates: Coordinates
    farmer_mobile: str = Field(pattern=r"^\+91\d{10}$")
    loan_amount: int = Field(ge=20000, le=50000)
    references: list[str]
    banker_id: str = Field(min_length=1)

    @field_validator("references")
    @classmethod
    def validate_references(cls, value: list[str]) -> list[str]:
        if len(value) != 2:
            raise ValueError("exactly 2 references are required")
        for mobile in value:
            if not re.match(r"^\+91\d{10}$", mobile):
                raise ValueError("each reference must match +91XXXXXXXXXX")
        return value


class AnalyzeFarmResponse(BaseModel):
    application_id: UUID
    status: ApplicationStatus
    message: str


class LayerScore(BaseModel):
    score: int | None = None
    status: str | None = None
    quality: float | None = None
    provider_status: str | None = None
    flags: list[str] = Field(default_factory=list)


class DebtLayerScore(LayerScore):
    existing_debt: int | None = None
    proposed_debt: int | None = None
    estimated_income: int | None = None
    debt_to_income_ratio: float | None = None


class SocialLayerScore(LayerScore):
    verified_references: int | None = None


class RiskScoreMetadata(BaseModel):
    created_at: datetime
    processing_time_seconds: int
    data_quality_flags: list[str] = Field(default_factory=list)


class RiskScoreResponse(BaseModel):
    application_id: UUID
    satellite: LayerScore
    debt: DebtLayerScore
    social: SocialLayerScore
    overall_score: int | None = None
    traffic_light_status: str | None = None
    rationale: str | None = None
    yellow_explanation: "YellowExplanationBundle | None" = None
    metadata: RiskScoreMetadata


class BankerApplicationItem(BaseModel):
    application_id: UUID
    farmer_mobile: str
    loan_amount: int
    status: str
    created_at: datetime
    overall_score: int | None = None
    traffic_light_status: str | None = None


class BankerApplicationsResponse(BaseModel):
    banker_id: str
    applications: list[BankerApplicationItem]


class DebtStatus(str, Enum):
    verified = "verified"
    timeout = "timeout"
    provider_unavailable = "provider_unavailable"
    consent_pending = "consent_pending"
    unverified = "unverified"


class ManualAction(str, Enum):
    approve = "approve"
    reject = "reject"
    escalate = "escalate"


class DecisionRequest(BaseModel):
    manual_action: ManualAction = ManualAction.escalate
    satellite_score: int = Field(ge=0, le=100)
    debt_score: int | None = Field(default=None, ge=0, le=100)
    social_score: int | None = Field(default=None, ge=0, le=100)
    satellite_data_quality: float = Field(ge=0.0, le=1.0)
    debt_to_income_ratio: float | None = Field(default=None, ge=0.0)
    debt_status: DebtStatus | None = None
    social_verified_references: int | None = Field(default=None, ge=0, le=2)
    satellite_no_crop_history: bool = False
    satellite_fire_detected: bool = False
    identity_verification_failed: bool = False
    rationale_override: str | None = None
    actor_id: str = Field(min_length=1, default="system")


class DecisionResponse(BaseModel):
    application_id: UUID
    assessment_id: UUID
    overall_score: int
    traffic_light_status: str
    status: ApplicationStatus
    rationale: str
    yellow_explanation: "YellowExplanationBundle | None" = None
    decision_rule_version: str | None = None
    decision_rule_id: str | None = None
    manual_action: ManualAction | None = None


class YellowExplanationBundle(BaseModel):
    primary_reasons: list[str] = Field(default_factory=list, max_length=3)
    missing_or_low_confidence_data: list[str] = Field(default_factory=list)
    recommended_manual_checks: list[str] = Field(default_factory=list)
    expected_impact_if_approved: str
    expected_impact_if_rejected: str


class DefaultPenaltyReference(BaseModel):
    reference_mobile: str
    trust_score_before: int
    trust_score_after: int


class SocialDefaultPenaltyResponse(BaseModel):
    application_id: UUID
    farmer_mobile: str
    farmer_trust_before: int
    farmer_trust_after: int
    impacted_references: list[DefaultPenaltyReference] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str
    correlation_id: str | None = None
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AgentRecommendationItem(BaseModel):
    action: ManualAction
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    primary_reasons: list[str] = Field(default_factory=list, max_length=3)
    required_checks: list[str] = Field(default_factory=list)
    expected_impact_if_approved: str
    expected_impact_if_rejected: str


class AgentRecommendationResponse(BaseModel):
    application_id: UUID
    generated_at: datetime
    traffic_light_status: str | None = None
    graph_path: list[str] = Field(default_factory=list)
    recommendation: AgentRecommendationItem
