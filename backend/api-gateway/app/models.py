from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    banker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    farmer_mobile: Mapped[str] = mapped_column(String(13), nullable=False)
    loan_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'processing'"), default="processing"
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FarmerReference(Base):
    __tablename__ = "farmer_references"

    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_applications.application_id"), nullable=False
    )
    farmer_mobile: Mapped[str] = mapped_column(String(13), nullable=False)
    reference_mobile: Mapped[str] = mapped_column(String(13), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'"), default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_applications.application_id"), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(
        Enum("system", "banker", "service", name="actor_type_enum"), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_applications.application_id"), nullable=False
    )
    satellite_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    satellite_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    satellite_flags: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'::jsonb")
    )
    satellite_provider_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'"), default="pending"
    )
    satellite_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    debt_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debt_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'"), default="pending"
    )
    debt_provider_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'"), default="pending"
    )
    debt_flags: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'::jsonb")
    )
    debt_existing_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debt_proposed_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debt_estimated_income: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debt_to_income_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    social_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    social_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'"), default="pending"
    )
    social_provider_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'"), default="pending"
    )
    social_flags: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'::jsonb")
    )
    social_verified_references: Mapped[int | None] = mapped_column(Integer, nullable=True)
    social_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traffic_light_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision_rule_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_rule_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TrustNetwork(Base):
    __tablename__ = "trust_network"

    trust_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farmer_mobile: Mapped[str] = mapped_column(String(13), nullable=False)
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("50"))
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JlgLinkage(Base):
    __tablename__ = "jlg_linkages"

    linkage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_applications.application_id"), nullable=True
    )
    farmer_mobile: Mapped[str] = mapped_column(String(13), nullable=False)
    reference_mobile: Mapped[str] = mapped_column(String(13), nullable=False)
    linkage_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'"), default="pending"
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
