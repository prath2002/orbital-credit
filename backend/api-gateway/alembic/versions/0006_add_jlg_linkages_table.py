"""add jlg linkages table

Revision ID: 0006_jlg_linkages
Revises: 0005_social_assessment_fields
Create Date: 2026-03-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0006_jlg_linkages"
down_revision: str | None = "0005_social_assessment_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jlg_linkages",
        sa.Column("linkage_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loan_applications.application_id"), nullable=True),
        sa.Column("farmer_mobile", sa.String(length=13), nullable=False),
        sa.Column("reference_mobile", sa.String(length=13), nullable=False),
        sa.Column("linkage_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_jlg_linkages_farmer_reference",
        "jlg_linkages",
        ["farmer_mobile", "reference_mobile"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_jlg_linkages_farmer_reference", table_name="jlg_linkages")
    op.drop_table("jlg_linkages")

