from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class CircuitBreaker:
    failure_threshold: int
    reset_seconds: int
    failure_count: int = 0
    state: str = "closed"
    opened_at: datetime | None = None
    last_error: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def allow_request(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.state == "open":
            if self.opened_at is None:
                return False
            if now >= self.opened_at + timedelta(seconds=self.reset_seconds):
                self.state = "half_open"
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"
        self.opened_at = None
        self.last_error = None

    def record_failure(self, error_name: str) -> None:
        self.failure_count += 1
        self.last_error = error_name
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.opened_at = datetime.now(timezone.utc)
