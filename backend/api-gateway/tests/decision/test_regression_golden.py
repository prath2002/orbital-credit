from __future__ import annotations

from dataclasses import dataclass

from app.schemas import DebtStatus, DecisionRequest
from app.services.decision_engine import DecisionEngine


@dataclass(frozen=True)
class GoldenCase:
    name: str
    payload: DecisionRequest
    expected_zone: str
    expected_rule_prefix: str


def _base_payload() -> DecisionRequest:
    return DecisionRequest(
        satellite_score=82,
        debt_score=64,
        social_score=72,
        satellite_data_quality=0.90,
        debt_to_income_ratio=0.29,
        debt_status=DebtStatus.verified,
        social_verified_references=2,
        satellite_no_crop_history=False,
        satellite_fire_detected=False,
        identity_verification_failed=False,
        actor_id="system",
    )


def _golden_cases() -> list[GoldenCase]:
    base = _base_payload()
    return [
        GoldenCase(
            name="red_no_crop_history",
            payload=base.model_copy(update={"satellite_no_crop_history": True}),
            expected_zone="RED",
            expected_rule_prefix="R-RED-01",
        ),
        GoldenCase(
            name="red_fire_detected",
            payload=base.model_copy(update={"satellite_fire_detected": True}),
            expected_zone="RED",
            expected_rule_prefix="R-RED-02",
        ),
        GoldenCase(
            name="red_high_dti",
            payload=base.model_copy(update={"debt_to_income_ratio": 0.51}),
            expected_zone="RED",
            expected_rule_prefix="R-RED-03",
        ),
        GoldenCase(
            name="red_reference_shortfall",
            payload=base.model_copy(update={"social_verified_references": 1}),
            expected_zone="RED",
            expected_rule_prefix="R-RED-04",
        ),
        GoldenCase(
            name="red_identity_failed",
            payload=base.model_copy(update={"identity_verification_failed": True}),
            expected_zone="RED",
            expected_rule_prefix="R-RED-05",
        ),
        GoldenCase(
            name="green_satellite_gate",
            payload=base,
            expected_zone="GREEN",
            expected_rule_prefix="R-GREEN-01",
        ),
        GoldenCase(
            name="green_debt_gate_when_satellite_not_green",
            payload=base.model_copy(
                update={
                    "satellite_score": 75,
                    "satellite_data_quality": 0.85,
                    "debt_to_income_ratio": 0.25,
                    "debt_status": DebtStatus.verified,
                    "social_score": 50,
                }
            ),
            expected_zone="GREEN",
            expected_rule_prefix="R-GREEN-02",
        ),
        GoldenCase(
            name="green_social_gate_when_others_not_green",
            payload=base.model_copy(
                update={
                    "satellite_score": 70,
                    "satellite_data_quality": 0.82,
                    "debt_to_income_ratio": 0.40,
                    "social_score": 75,
                    "social_verified_references": 2,
                }
            ),
            expected_zone="GREEN",
            expected_rule_prefix="R-GREEN-03",
        ),
        GoldenCase(
            name="yellow_low_satellite_quality",
            payload=base.model_copy(
                update={
                    "satellite_score": 70,
                    "satellite_data_quality": 0.70,
                    "debt_status": DebtStatus.timeout,
                    "social_score": 50,
                }
            ),
            expected_zone="YELLOW",
            expected_rule_prefix="R-YELLOW-01",
        ),
        GoldenCase(
            name="yellow_debt_provider_incomplete",
            payload=base.model_copy(
                update={
                    "satellite_score": 70,
                    "satellite_data_quality": 0.85,
                    "debt_status": DebtStatus.provider_unavailable,
                    "social_score": 50,
                }
            ),
            expected_zone="YELLOW",
            expected_rule_prefix="R-YELLOW-02",
        ),
        GoldenCase(
            name="yellow_borderline_ranges",
            payload=base.model_copy(
                update={
                    "satellite_score": 65,
                    "satellite_data_quality": 0.85,
                    "debt_status": DebtStatus.verified,
                    "debt_to_income_ratio": 0.35,
                    "social_score": 55,
                }
            ),
            expected_zone="YELLOW",
            expected_rule_prefix="R-YELLOW-03",
        ),
        GoldenCase(
            name="yellow_safe_default",
            payload=base.model_copy(
                update={
                    "satellite_score": 55,
                    "satellite_data_quality": 0.85,
                    "debt_status": DebtStatus.unverified,
                    "debt_to_income_ratio": 0.10,
                    "social_score": 30,
                    "social_verified_references": 2,
                }
            ),
            expected_zone="YELLOW",
            expected_rule_prefix="R-YELLOW-04",
        ),
    ]


def test_decision_golden_cases_regression() -> None:
    engine = DecisionEngine()
    for case in _golden_cases():
        zone, reasons = engine.evaluate_zone(case.payload)
        assert zone == case.expected_zone, case.name
        assert reasons and reasons[0].startswith(case.expected_rule_prefix), case.name


def test_decision_golden_cases_are_deterministic() -> None:
    engine = DecisionEngine()
    for case in _golden_cases():
        first = engine.evaluate_zone(case.payload)
        second = engine.evaluate_zone(case.payload)
        assert first == second, case.name
