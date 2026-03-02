from __future__ import annotations


class DebtServiceError(Exception):
    def __init__(self, *, message: str, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class DebtTimeoutError(DebtServiceError):
    def __init__(self, operation: str) -> None:
        super().__init__(
            message=f"Debt operation timed out: {operation}",
            code="DEBT_PROVIDER_TIMEOUT",
            retryable=True,
        )


class DebtProviderUnavailableError(DebtServiceError):
    def __init__(self, operation: str) -> None:
        super().__init__(
            message=f"Debt provider unavailable: {operation}",
            code="DEBT_PROVIDER_UNAVAILABLE",
            retryable=True,
        )


class DebtCircuitOpenError(DebtServiceError):
    def __init__(self, operation: str) -> None:
        super().__init__(
            message=f"Debt provider circuit is open: {operation}",
            code="DEBT_PROVIDER_CIRCUIT_OPEN",
            retryable=True,
        )

