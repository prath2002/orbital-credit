"""add social assessment fields

Revision ID: 0005_social_assessment_fields
Revises: 0004_debt_metric_fields
Create Date: 2026-03-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0005_social_assessment_fields"
down_revision: str | None = "0004_debt_metric_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "risk_assessments",
        sa.Column("social_status", sa.String(length=30), nullable=False, server_default="pending"),
    )
    op.add_column(
        "risk_assessments",
        sa.Column("social_provider_status", sa.String(length=30), nullable=False, server_default="pending"),
    )
    op.add_column(
        "risk_assessments",
        sa.Column(
            "social_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("risk_assessments", sa.Column("social_verified_references", sa.Integer(), nullable=True))
    op.add_column("risk_assessments", sa.Column("social_computed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_assessments", "social_computed_at")
    op.drop_column("risk_assessments", "social_verified_references")
    op.drop_column("risk_assessments", "social_flags")
    op.drop_column("risk_assessments", "social_provider_status")
    op.drop_column("risk_assessments", "social_status")

