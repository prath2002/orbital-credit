from __future__ import annotations


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


class ProviderError(DomainError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 502,
        retryable: bool = True,
    ) -> None:
        super().__init__(code, message, status_code=status_code, retryable=retryable)


class ValidationError(DomainError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 422,
        retryable: bool = False,
    ) -> None:
        super().__init__(code, message, status_code=status_code, retryable=retryable)


class SystemError(DomainError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 500,
        retryable: bool = True,
    ) -> None:
        super().__init__(code, message, status_code=status_code, retryable=retryable)
