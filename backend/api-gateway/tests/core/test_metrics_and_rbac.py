from __future__ import annotations

from app.core.errors import ValidationError
from app.core.metrics import MetricsRegistry
from app.core.rbac import Role, require_roles


def test_metrics_registry_renders_expected_metrics() -> None:
    metrics = MetricsRegistry()
    metrics.observe_analysis_latency_seconds(2.5)
    metrics.observe_analysis_latency_seconds(1.5)
    metrics.increment_decision_zone("GREEN")
    metrics.increment_external_api_failure(
        provider="debt-provider",
        operation="debt_assess",
        error_code="DEBT_PROVIDER_TIMEOUT",
    )
    metrics.increment_data_quality_low()

    rendered = metrics.render_prometheus()
    assert "analysis_latency_seconds 2.000000" in rendered
    assert 'decision_zone_count{zone="GREEN"} 1' in rendered
    assert 'external_api_failures_total{provider="debt-provider",operation="debt_assess",error_code="DEBT_PROVIDER_TIMEOUT"} 1' in rendered
    assert "data_quality_low_total 1" in rendered


def test_rbac_rejects_disallowed_role() -> None:
    dependency = require_roles([Role.ops_admin])
    try:
        dependency(x_actor_id="banker-1", x_actor_role="banker")
    except ValidationError as exc:
        assert exc.code == "RBAC_FORBIDDEN"
    else:
        raise AssertionError("Expected RBAC_FORBIDDEN")

