from __future__ import annotations

from collections import Counter
from threading import Lock
from time import perf_counter


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()
        self._latency_sum = 0.0
        self._latency_count = 0

    def observe_analysis_latency_seconds(self, duration_seconds: float) -> None:
        with self._lock:
            self._latency_sum += max(0.0, duration_seconds)
            self._latency_count += 1

    def increment_external_api_failure(self, *, provider: str, operation: str, error_code: str) -> None:
        with self._lock:
            key = f'external_api_failures_total|provider="{provider}",operation="{operation}",error_code="{error_code}"'
            self._counters[key] += 1

    def increment_decision_zone(self, zone: str) -> None:
        normalized = (zone or "UNKNOWN").upper()
        with self._lock:
            key = f'decision_zone_count|zone="{normalized}"'
            self._counters[key] += 1

    def increment_data_quality_low(self) -> None:
        with self._lock:
            self._counters["data_quality_low_total"] += 1

    def render_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP analysis_latency_seconds Average analyze-farm latency in seconds",
                "# TYPE analysis_latency_seconds gauge",
            ]
            avg = (self._latency_sum / self._latency_count) if self._latency_count else 0.0
            lines.append(f"analysis_latency_seconds {avg:.6f}")

            lines.extend(
                [
                    "# HELP external_api_failures_total Total external adapter failures",
                    "# TYPE external_api_failures_total counter",
                ]
            )
            lines.extend(
                [
                    "# HELP decision_zone_count Total finalized decision counts by zone",
                    "# TYPE decision_zone_count counter",
                ]
            )
            lines.extend(
                [
                    "# HELP data_quality_low_total Total low-quality satellite outcomes",
                    "# TYPE data_quality_low_total counter",
                ]
            )

            for raw_key, value in sorted(self._counters.items()):
                if "|" in raw_key:
                    metric, labels = raw_key.split("|", 1)
                    lines.append(f"{metric}{{{labels}}} {value}")
                else:
                    lines.append(f"{raw_key} {value}")
            return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()


class Timer:
    def __init__(self) -> None:
        self._start = perf_counter()

    def elapsed_seconds(self) -> float:
        return perf_counter() - self._start

