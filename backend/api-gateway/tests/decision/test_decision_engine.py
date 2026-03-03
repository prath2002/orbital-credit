from __future__ import annotations

from types import SimpleNamespace

from app.schemas import DebtStatus, DecisionRequest
from app.services.decision_engine import DecisionEngine


def _base_payload() -> DecisionRequest:
    return DecisionRequest(
        satellite_score=82,
        debt_score=64,
        social_score=72,
        satellite_data_quality=0.9,
        debt_to_income_ratio=0.29,
        debt_status=DebtStatus.verified,
        social_verified_references=2,
        actor_id="system",
    )


def test_compute_overall_score_weighting() -> None:
    engine = DecisionEngine()
    score = engine.compute_overall_score(
        satellite_score=80,
        debt_score=70,
        social_score=60,
    )
    assert score == 72


def test_resolve_inputs_backfills_from_assessment() -> None:
    engine = DecisionEngine()
    payload = DecisionRequest(
        satellite_score=82,
        debt_score=None,
        social_score=None,
        satellite_data_quality=0.9,
        debt_to_income_ratio=None,
        debt_status=None,
        social_verified_references=None,
        actor_id="system",
    )
    assessment = SimpleNamespace(
        debt_score=65,
        debt_to_income_ratio=0.33,
        debt_status="verified",
        social_score=59,
        social_verified_references=1,
    )

    resolved = engine.resolve_inputs(payload=payload, assessment=assessment)

    assert resolved.debt_score == 65
    assert resolved.debt_to_income_ratio == 0.33
    assert resolved.debt_status == DebtStatus.verified
    assert resolved.social_score == 59
    assert resolved.social_verified_references == 1


def test_evaluate_zone_red_for_low_reference_verification() -> None:
    engine = DecisionEngine()
    payload = _base_payload().model_copy(update={"social_verified_references": 1})
    zone, reasons = engine.evaluate_zone(payload)

    assert zone == "RED"
    assert reasons[0].startswith("R-RED-04")


def test_evaluate_zone_green_when_all_gates_met() -> None:
    engine = DecisionEngine()
    zone, reasons = engine.evaluate_zone(_base_payload())

    assert zone == "GREEN"
    assert reasons[0].startswith("R-GREEN-01")


def test_rule_priority_first_match_wins_for_green_01_before_other_checks() -> None:
    engine = DecisionEngine()
    payload = _base_payload().model_copy(
        update={
            "debt_status": DebtStatus.consent_pending,
            "debt_to_income_ratio": 0.45,
            "social_score": 42,
            "social_verified_references": 2,
        }
    )

    zone, reasons = engine.evaluate_zone(payload)

    assert zone == "GREEN"
    assert reasons[0].startswith("R-GREEN-01")


def test_rule_priority_yellow_01_precedes_yellow_02() -> None:
    engine = DecisionEngine()
    payload = _base_payload().model_copy(
        update={
            "satellite_score": 70,
            "satellite_data_quality": 0.70,
            "debt_status": DebtStatus.timeout,
            "social_score": 45,
        }
    )

    zone, reasons = engine.evaluate_zone(payload)

    assert zone == "YELLOW"
    assert reasons[0].startswith("R-YELLOW-01")


def test_build_yellow_explanation_contains_required_sections() -> None:
    engine = DecisionEngine()
    payload = _base_payload().model_copy(
        update={
            "satellite_score": 70,
            "satellite_data_quality": 0.70,
            "debt_status": DebtStatus.timeout,
            "debt_to_income_ratio": 0.44,
            "social_score": 55,
            "social_verified_references": 2,
        }
    )
    zone, reasons = engine.evaluate_zone(payload)
    assert zone == "YELLOW"

    explanation = engine.build_yellow_explanation(payload=payload, reasons=reasons)

    assert len(explanation.primary_reasons) >= 1
    assert len(explanation.recommended_manual_checks) >= 1
    assert "Satellite imagery quality" in " ".join(explanation.missing_or_low_confidence_data)
    assert explanation.expected_impact_if_approved
    assert explanation.expected_impact_if_rejected


def test_extract_rule_id_from_reason() -> None:
    engine = DecisionEngine()
    assert engine.extract_rule_id("R-YELLOW-02: Debt provider verification incomplete") == "R-YELLOW-02"
    assert engine.extract_rule_id("Manual review required") is None
