from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.errors import ValidationError
from app.main import _resolve_debt_inputs
from app.schemas import DebtStatus, DecisionRequest


def _base_payload() -> DecisionRequest:
    return DecisionRequest(
        satellite_score=82,
        debt_score=None,
        social_score=72,
        satellite_data_quality=0.9,
        debt_to_income_ratio=None,
        debt_status=None,
        social_verified_references=2,
        actor_id="system",
    )


def test_resolve_debt_inputs_uses_assessment_when_payload_missing() -> None:
    payload = _base_payload()
    assessment = SimpleNamespace(
        debt_score=66,
        debt_to_income_ratio=0.29,
        debt_status="verified",
    )

    score, ratio, status = _resolve_debt_inputs(payload=payload, assessment=assessment)

    assert score == 66
    assert ratio == 0.29
    assert status == DebtStatus.verified


def test_resolve_debt_inputs_prefers_payload_over_assessment() -> None:
    payload = DecisionRequest(
        satellite_score=82,
        debt_score=59,
        social_score=72,
        satellite_data_quality=0.9,
        debt_to_income_ratio=0.41,
        debt_status=DebtStatus.timeout,
        social_verified_references=2,
        actor_id="system",
    )
    assessment = SimpleNamespace(
        debt_score=66,
        debt_to_income_ratio=0.29,
        debt_status="verified",
    )

    score, ratio, status = _resolve_debt_inputs(payload=payload, assessment=assessment)

    assert score == 59
    assert ratio == 0.41
    assert status == DebtStatus.timeout


def test_resolve_debt_inputs_raises_for_incomplete_inputs() -> None:
    payload = _base_payload()
    assessment = SimpleNamespace(
        debt_score=None,
        debt_to_income_ratio=None,
        debt_status="pending",
    )

    with pytest.raises(ValidationError) as exc:
        _resolve_debt_inputs(payload=payload, assessment=assessment)

    assert exc.value.code == "DEBT_INPUT_INCOMPLETE"

