"""add satellite assessment linkage fields

Revision ID: 0002_satellite_fields
Revises: 0001_initial_core_tables
Create Date: 2026-02-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_satellite_fields"
down_revision: str | None = "0001_initial_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("risk_assessments", sa.Column("satellite_quality", sa.Float(), nullable=True))
    op.add_column(
        "risk_assessments",
        sa.Column(
            "satellite_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "risk_assessments",
        sa.Column(
            "satellite_provider_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "risk_assessments",
        sa.Column("satellite_computed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("risk_assessments", "satellite_computed_at")
    op.drop_column("risk_assessments", "satellite_provider_status")
    op.drop_column("risk_assessments", "satellite_flags")
    op.drop_column("risk_assessments", "satellite_quality")
