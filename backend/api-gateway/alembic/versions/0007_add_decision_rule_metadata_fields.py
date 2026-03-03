"""add decision rule metadata fields

Revision ID: 0007_decision_rule_metadata
Revises: 0006_jlg_linkages
Create Date: 2026-03-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_decision_rule_metadata"
down_revision: str | None = "0006_jlg_linkages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "risk_assessments",
        sa.Column("decision_rule_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "risk_assessments",
        sa.Column("decision_rule_id", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("risk_assessments", "decision_rule_id")
    op.drop_column("risk_assessments", "decision_rule_version")

