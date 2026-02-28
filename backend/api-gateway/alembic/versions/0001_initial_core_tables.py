"""create initial core tables

Revision ID: 0001_initial_core_tables
Revises:
Create Date: 2026-02-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_core_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


actor_type_enum = postgresql.ENUM(
    "system",
    "banker",
    "service",
    name="actor_type_enum",
    create_type=False,
)


def upgrade() -> None:
    actor_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "loan_applications",
        sa.Column("application_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("banker_id", sa.String(length=100), nullable=False),
        sa.Column("farmer_mobile", sa.String(length=13), nullable=False),
        sa.Column("loan_amount", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="processing"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_loan_applications_banker_created", "loan_applications", ["banker_id", "created_at"], unique=False)

    op.create_table(
        "risk_assessments",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loan_applications.application_id"), nullable=False),
        sa.Column("satellite_score", sa.Integer(), nullable=True),
        sa.Column("debt_score", sa.Integer(), nullable=True),
        sa.Column("social_score", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("traffic_light_status", sa.String(length=20), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_risk_assessments_app_created", "risk_assessments", ["application_id", "created_at"], unique=False)

    op.create_table(
        "trust_network",
        sa.Column("trust_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("farmer_mobile", sa.String(length=13), nullable=False),
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "farmer_references",
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loan_applications.application_id"), nullable=False),
        sa.Column("farmer_mobile", sa.String(length=13), nullable=False),
        sa.Column("reference_mobile", sa.String(length=13), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_farmer_references_farmer_mobile", "farmer_references", ["farmer_mobile"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loan_applications.application_id"), nullable=True),
        sa.Column("actor_type", actor_type_enum, nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_events_app_created", "audit_events", ["application_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_app_created", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_farmer_references_farmer_mobile", table_name="farmer_references")
    op.drop_table("farmer_references")

    op.drop_table("trust_network")

    op.drop_index("ix_risk_assessments_app_created", table_name="risk_assessments")
    op.drop_table("risk_assessments")

    op.drop_index("ix_loan_applications_banker_created", table_name="loan_applications")
    op.drop_table("loan_applications")

    actor_type_enum.drop(op.get_bind(), checkfirst=True)
