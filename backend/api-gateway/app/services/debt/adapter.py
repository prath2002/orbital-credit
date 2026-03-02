from __future__ import annotations

from typing import Protocol

from app.services.debt.models import DebtAssessmentResult


class DebtProviderAdapter(Protocol):
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        """Return debt consent status and optional debt score."""

