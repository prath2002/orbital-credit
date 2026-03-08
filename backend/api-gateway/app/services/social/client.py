from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import random
from time import sleep
from typing import Callable, TypeVar

from app.config import settings
from app.core.logging import log_event
from app.core.metrics import metrics_registry
from app.services.social.adapter import SocialProviderAdapter
from app.services.social.exceptions import (
    SocialCircuitOpenError,
    SocialProviderUnavailableError,
    SocialServiceError,
    SocialTimeoutError,
)
from app.services.social.models import SocialAssessmentResult, SocialStatus
from app.services.social.models import ReferenceVerificationResult, ReferenceVerificationStatus
from app.services.social.resilience import CircuitBreaker


T = TypeVar("T")


def _reference_status(mobile: str) -> ReferenceVerificationStatus:
    if not mobile or not mobile[-1].isdigit():
        return ReferenceVerificationStatus.failed
    digit = int(mobile[-1])
    if digit <= 6:
        return ReferenceVerificationStatus.verified
    if digit <= 8:
        return ReferenceVerificationStatus.failed
    return ReferenceVerificationStatus.pending


def _status_and_score_from_verified_count(verified_references: int, farmer_mobile: str) -> tuple[SocialStatus, int]:
    seed = sum(int(ch) for ch in farmer_mobile if ch.isdigit()) % 7
    if verified_references == 2:
        return SocialStatus.verified, 72 + seed
    if verified_references == 1:
        return SocialStatus.partial, 48 + seed
    return SocialStatus.unverified, 30 + seed


class MockSocialProvider:
    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        verifications = [
            ReferenceVerificationResult(
                reference_mobile=mobile,
                status=_reference_status(mobile),
            )
            for mobile in reference_mobiles[:2]
        ]
        verified_references = sum(1 for item in verifications if item.status == ReferenceVerificationStatus.verified)
        status, score = _status_and_score_from_verified_count(verified_references, farmer_mobile)
        flags = [f"verified_references:{verified_references}", f"social_status:{status.value}"]
        if any(item.status == ReferenceVerificationStatus.pending for item in verifications):
            flags.append("reference_verification_pending")
        if status != SocialStatus.verified:
            flags.append("manual_review_required")
        return SocialAssessmentResult(
            social_status=status,
            social_score=score,
            verified_references=verified_references,
            reference_verifications=verifications,
            provider_status="mock",
            flags=flags,
        )


class DeferredSocialProvider:
    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        _ = farmer_mobile, reference_mobiles
        return SocialAssessmentResult(
            social_status=SocialStatus.provider_unavailable,
            social_score=None,
            verified_references=0,
            reference_verifications=[
                ReferenceVerificationResult(
                    reference_mobile=mobile,
                    status=ReferenceVerificationStatus.provider_unavailable,
                )
                for mobile in reference_mobiles[:2]
            ],
            provider_status="social_deferred",
            flags=["social_real_not_enabled", "manual_review_required"],
        )


class SocialTrustClient:
    def __init__(self, adapter: SocialProviderAdapter | None = None) -> None:
        self.adapter = adapter or self._default_adapter()
        self._breakers: dict[str, CircuitBreaker] = {}

    @staticmethod
    def _default_adapter() -> SocialProviderAdapter:
        if settings.social_provider_mode == "real":
            return DeferredSocialProvider()
        return MockSocialProvider()

    def _breaker_for(self, operation: str) -> CircuitBreaker:
        breaker = self._breakers.get(operation)
        if breaker is None:
            breaker = CircuitBreaker(
                failure_threshold=settings.social_circuit_breaker_failure_threshold,
                reset_seconds=settings.social_circuit_breaker_reset_seconds,
            )
            self._breakers[operation] = breaker
        return breaker

    def _execute_with_resilience(self, operation: str, fn: Callable[[], T]) -> T:
        breaker = self._breaker_for(operation)
        if not breaker.allow_request():
            raise SocialCircuitOpenError(operation)

        delay = settings.social_retry_base_delay_seconds
        attempts = max(1, settings.social_retry_attempts)
        last_exc: SocialServiceError | None = None
        for attempt in range(1, attempts + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(fn)
                    try:
                        result = future.result(timeout=settings.social_request_timeout_seconds)
                    except FuturesTimeoutError as exc:
                        future.cancel()
                        raise SocialTimeoutError(operation) from exc
                breaker.record_success()
                if attempt > 1:
                    log_event(
                        event="social_retry_recovered",
                        payload={"operation": operation, "attempt": attempt},
                    )
                return result
            except SocialServiceError as exc:
                last_exc = exc
            except Exception as exc:  # pragma: no cover - external provider path
                last_exc = SocialProviderUnavailableError(operation)
                last_exc.__cause__ = exc

            breaker.record_failure(last_exc.code if last_exc else "UNKNOWN")
            metrics_registry.increment_external_api_failure(
                provider="social-provider",
                operation=operation,
                error_code=(last_exc.code if last_exc else "UNKNOWN"),
            )
            log_event(
                level="ERROR",
                event="social_operation_failed",
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
    def _degraded_result(*, provider_status: str, code: str) -> SocialAssessmentResult:
        return SocialAssessmentResult(
            social_status=SocialStatus.provider_unavailable,
            social_score=None,
            verified_references=0,
            reference_verifications=[],
            provider_status=provider_status,
            flags=[f"social_error_code:{code}", "manual_review_required"],
        )

    def assess(self, *, farmer_mobile: str, reference_mobiles: list[str]) -> SocialAssessmentResult:
        try:
            result = self._execute_with_resilience(
                "social_assess",
                lambda: self.adapter.assess(
                    farmer_mobile=farmer_mobile,
                    reference_mobiles=reference_mobiles,
                ),
            )
            result.flags = sorted(set(result.flags))
            return result
        except SocialCircuitOpenError as exc:
            return self._degraded_result(provider_status="circuit_open", code=exc.code)
        except SocialTimeoutError as exc:
            return self._degraded_result(provider_status="timeout", code=exc.code)
        except SocialProviderUnavailableError as exc:
            return self._degraded_result(provider_status="provider_unavailable", code=exc.code)
        except SocialServiceError as exc:
            return self._degraded_result(provider_status="provider_error", code=exc.code)
