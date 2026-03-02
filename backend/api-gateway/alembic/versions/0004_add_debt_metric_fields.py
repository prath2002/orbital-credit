"""add debt metric fields

Revision ID: 0004_debt_metric_fields
Revises: 0003_debt_status_fields
Create Date: 2026-03-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_debt_metric_fields"
down_revision: str | None = "0003_debt_status_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("risk_assessments", sa.Column("debt_existing_amount", sa.Integer(), nullable=True))
    op.add_column("risk_assessments", sa.Column("debt_proposed_amount", sa.Integer(), nullable=True))
    op.add_column("risk_assessments", sa.Column("debt_estimated_income", sa.Integer(), nullable=True))
    op.add_column("risk_assessments", sa.Column("debt_to_income_ratio", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_assessments", "debt_to_income_ratio")
    op.drop_column("risk_assessments", "debt_estimated_income")
    op.drop_column("risk_assessments", "debt_proposed_amount")
    op.drop_column("risk_assessments", "debt_existing_amount")

