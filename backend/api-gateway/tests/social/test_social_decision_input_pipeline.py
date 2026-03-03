from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.errors import ValidationError
from app.main import _resolve_social_inputs
from app.schemas import DecisionRequest, DebtStatus


def _base_payload() -> DecisionRequest:
    return DecisionRequest(
        satellite_score=82,
        debt_score=60,
        social_score=None,
        satellite_data_quality=0.9,
        debt_to_income_ratio=0.29,
        debt_status=DebtStatus.verified,
        social_verified_references=None,
        actor_id="system",
    )


def test_resolve_social_inputs_uses_assessment_when_payload_missing() -> None:
    payload = _base_payload()
    assessment = SimpleNamespace(
        social_score=67,
        social_verified_references=2,
    )

    score, verified_refs = _resolve_social_inputs(payload=payload, assessment=assessment)

    assert score == 67
    assert verified_refs == 2


def test_resolve_social_inputs_prefers_payload_over_assessment() -> None:
    payload = DecisionRequest(
        satellite_score=82,
        debt_score=60,
        social_score=49,
        satellite_data_quality=0.9,
        debt_to_income_ratio=0.29,
        debt_status=DebtStatus.verified,
        social_verified_references=1,
        actor_id="system",
    )
    assessment = SimpleNamespace(
        social_score=67,
        social_verified_references=2,
    )

    score, verified_refs = _resolve_social_inputs(payload=payload, assessment=assessment)

    assert score == 49
    assert verified_refs == 1


def test_resolve_social_inputs_raises_for_incomplete_inputs() -> None:
    payload = _base_payload()
    assessment = SimpleNamespace(
        social_score=None,
        social_verified_references=None,
    )

    with pytest.raises(ValidationError) as exc:
        _resolve_social_inputs(payload=payload, assessment=assessment)

    assert exc.value.code == "SOCIAL_INPUT_INCOMPLETE"

