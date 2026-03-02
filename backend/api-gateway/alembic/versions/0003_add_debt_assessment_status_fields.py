"""add debt assessment status fields

Revision ID: 0003_debt_status_fields
Revises: 0002_satellite_fields
Create Date: 2026-03-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0003_debt_status_fields"
down_revision: str | None = "0002_satellite_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "risk_assessments",
        sa.Column("debt_status", sa.String(length=30), nullable=False, server_default="pending"),
    )
    op.add_column(
        "risk_assessments",
        sa.Column(
            "debt_provider_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "risk_assessments",
        sa.Column(
            "debt_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "risk_assessments",
        sa.Column("debt_computed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("risk_assessments", "debt_computed_at")
    op.drop_column("risk_assessments", "debt_flags")
    op.drop_column("risk_assessments", "debt_provider_status")
    op.drop_column("risk_assessments", "debt_status")

