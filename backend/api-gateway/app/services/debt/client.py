from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import random
from time import sleep
from typing import Callable, TypeVar

from app.config import settings
from app.core.logging import log_event
from app.core.metrics import metrics_registry
from app.services.debt.adapter import DebtProviderAdapter
from app.services.debt.exceptions import (
    DebtCircuitOpenError,
    DebtProviderUnavailableError,
    DebtServiceError,
    DebtTimeoutError,
)
from app.services.debt.models import DebtAssessmentResult, DebtConsentState
from app.services.debt.resilience import CircuitBreaker


T = TypeVar("T")


def _score_from_ratio(debt_to_income_ratio: float) -> int:
    raw = round(100 - (debt_to_income_ratio * 120.0))
    return max(0, min(100, raw))


def _status_from_mobile(farmer_mobile: str) -> DebtConsentState:
    last_digit = 9
    if farmer_mobile and farmer_mobile[-1].isdigit():
        last_digit = int(farmer_mobile[-1])

    if last_digit <= 3:
        return DebtConsentState.verified
    if last_digit == 4:
        return DebtConsentState.timeout
    if last_digit == 5:
        return DebtConsentState.provider_unavailable
    return DebtConsentState.consent_pending


def _build_verified_metrics(*, farmer_mobile: str, loan_amount: int) -> dict[str, int | float]:
    digit_seed = sum(int(ch) for ch in farmer_mobile if ch.isdigit())
    existing_debt = 5000 + ((digit_seed * 137) % 21001)
    estimated_income = 70000 + ((digit_seed * 211) % 60001)
    proposed_debt = existing_debt + loan_amount
    debt_to_income_ratio = round(proposed_debt / estimated_income, 4)
    return {
        "existing_debt": existing_debt,
        "proposed_debt": proposed_debt,
        "estimated_income": estimated_income,
        "debt_to_income_ratio": debt_to_income_ratio,
    }


class MockDebtProvider:
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        consent_state = _status_from_mobile(farmer_mobile)
        flags = [f"consent_state:{consent_state.value}"]
        if consent_state != DebtConsentState.verified:
            flags.append("manual_review_required")

        if consent_state == DebtConsentState.verified:
            metrics = _build_verified_metrics(farmer_mobile=farmer_mobile, loan_amount=loan_amount)
            debt_score = _score_from_ratio(metrics["debt_to_income_ratio"])
            return DebtAssessmentResult(
                consent_state=consent_state,
                debt_score=debt_score,
                existing_debt=metrics["existing_debt"],
                proposed_debt=metrics["proposed_debt"],
                estimated_income=metrics["estimated_income"],
                debt_to_income_ratio=metrics["debt_to_income_ratio"],
                provider_status="mock",
                flags=flags,
            )

        return DebtAssessmentResult(
            consent_state=consent_state,
            debt_score=None,
            existing_debt=None,
            proposed_debt=None,
            estimated_income=None,
            debt_to_income_ratio=None,
            provider_status="mock",
            flags=flags,
        )


class DeferredAAProvider:
    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        _ = farmer_mobile, loan_amount
        return DebtAssessmentResult(
            consent_state=DebtConsentState.consent_pending,
            debt_score=None,
            existing_debt=None,
            proposed_debt=None,
            estimated_income=None,
            debt_to_income_ratio=None,
            provider_status="aa_deferred",
            flags=["aa_real_not_enabled", "manual_review_required"],
        )


class DebtServiceClient:
    def __init__(self, adapter: DebtProviderAdapter | None = None) -> None:
        self.adapter = adapter or self._default_adapter()
        self._breakers: dict[str, CircuitBreaker] = {}

    @staticmethod
    def _default_adapter() -> DebtProviderAdapter:
        if settings.debt_provider_mode == "aa_real":
            return DeferredAAProvider()
        return MockDebtProvider()

    def _breaker_for(self, operation: str) -> CircuitBreaker:
        breaker = self._breakers.get(operation)
        if breaker is None:
            breaker = CircuitBreaker(
                failure_threshold=settings.debt_circuit_breaker_failure_threshold,
                reset_seconds=settings.debt_circuit_breaker_reset_seconds,
            )
            self._breakers[operation] = breaker
        return breaker

    @staticmethod
    def _call_with_timeout(fn: Callable[[], T], *, timeout_seconds: float) -> T:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError as exc:
                future.cancel()
                raise DebtTimeoutError("debt_assess") from exc

    def _execute_with_resilience(self, operation: str, fn: Callable[[], T]) -> T:
        breaker = self._breaker_for(operation)
        if not breaker.allow_request():
            raise DebtCircuitOpenError(operation)

        delay = settings.debt_retry_base_delay_seconds
        attempts = max(1, settings.debt_retry_attempts)
        last_exc: DebtServiceError | None = None
        for attempt in range(1, attempts + 1):
            try:
                result = self._call_with_timeout(
                    fn,
                    timeout_seconds=settings.debt_request_timeout_seconds,
                )
                breaker.record_success()
                if attempt > 1:
                    log_event(
                        event="debt_retry_recovered",
                        payload={"operation": operation, "attempt": attempt},
                    )
                return result
            except DebtServiceError as exc:
                last_exc = exc
            except Exception as exc:  # pragma: no cover - external provider path
                last_exc = DebtProviderUnavailableError(operation)
                last_exc.__cause__ = exc

            breaker.record_failure(last_exc.code if last_exc else "UNKNOWN")
            metrics_registry.increment_external_api_failure(
                provider="debt-provider",
                operation=operation,
                error_code=(last_exc.code if last_exc else "UNKNOWN"),
            )
            log_event(
                level="ERROR",
                event="debt_operation_failed",
                payload={
                    "operation": operation,
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "error_code": last_exc.code if last_exc else "UNKNOWN",
                    "circuit_state": breaker.state,
                    "failure_count": breaker.failure_count,
                },
            )
            if attempt >= attempts:
                break
            jitter = random.uniform(0.0, 0.25)
            sleep(delay + jitter)
            delay *= 2

        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _degraded_result(*, consent_state: DebtConsentState, provider_status: str, code: str) -> DebtAssessmentResult:
        return DebtAssessmentResult(
            consent_state=consent_state,
            debt_score=None,
            existing_debt=None,
            proposed_debt=None,
            estimated_income=None,
            debt_to_income_ratio=None,
            provider_status=provider_status,
            flags=[f"debt_error_code:{code}", "manual_review_required"],
        )

    def assess(self, *, farmer_mobile: str, loan_amount: int) -> DebtAssessmentResult:
        try:
            result = self._execute_with_resilience(
                "debt_assess",
                lambda: self.adapter.assess(
                    farmer_mobile=farmer_mobile,
                    loan_amount=loan_amount,
                ),
            )
            result.flags = sorted(set(result.flags))
            return result
        except DebtTimeoutError as exc:
            return self._degraded_result(
                consent_state=DebtConsentState.timeout,
                provider_status="timeout",
                code=exc.code,
            )
        except DebtCircuitOpenError as exc:
            return self._degraded_result(
                consent_state=DebtConsentState.provider_unavailable,
                provider_status="circuit_open",
                code=exc.code,
            )
        except DebtProviderUnavailableError as exc:
            return self._degraded_result(
                consent_state=DebtConsentState.provider_unavailable,
                provider_status="provider_unavailable",
                code=exc.code,
            )
        except DebtServiceError as exc:
            return self._degraded_result(
                consent_state=DebtConsentState.provider_unavailable,
                provider_status="provider_error",
                code=exc.code,
            )
