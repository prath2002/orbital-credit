from __future__ import annotations


class SocialServiceError(Exception):
    def __init__(self, *, message: str, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class SocialProviderUnavailableError(SocialServiceError):
    def __init__(self, operation: str) -> None:
        super().__init__(
            message=f"Social provider unavailable: {operation}",
            code="SOCIAL_PROVIDER_UNAVAILABLE",
            retryable=True,
        )


class SocialTimeoutError(SocialServiceError):
    def __init__(self, operation: str) -> None:
        super().__init__(
            message=f"Social operation timed out: {operation}",
            code="SOCIAL_PROVIDER_TIMEOUT",
            retryable=True,
        )


class SocialCircuitOpenError(SocialServiceError):
    def __init__(self, operation: str) -> None:
        super().__init__(
            message=f"Social provider circuit is open: {operation}",
            code="SOCIAL_PROVIDER_CIRCUIT_OPEN",
            retryable=True,
        )
