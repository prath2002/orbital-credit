from __future__ import annotations

import json
from threading import Lock
from time import time
from typing import Any

from app.config import settings
from app.core.logging import log_event

try:  # pragma: no cover - optional dependency path
    import redis
except Exception:  # pragma: no cover - optional dependency path
    redis = None


class InMemoryTtlStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._data: dict[str, tuple[str, float | None]] = {}

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and expires_at < time():
                self._data.pop(key, None)
                return None
            return value

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        expires_at = time() + max(1, ttl_seconds)
        with self._lock:
            self._data[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class CacheClient:
    def __init__(self) -> None:
        self._memory = InMemoryTtlStore()
        self._redis = None

        if settings.redis_enabled and redis is not None:
            try:
                self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                self._redis.ping()
                log_event(event="cache_connected", payload={"backend": "redis"})
            except Exception as exc:  # pragma: no cover - external dependency path
                self._redis = None
                log_event(
                    level="ERROR",
                    event="cache_redis_unavailable",
                    payload={"error_type": type(exc).__name__, "fallback": "in_memory"},
                )
        else:
            log_event(event="cache_fallback_in_memory")

    def _get_raw(self, key: str) -> str | None:
        if self._redis is not None:
            try:
                return self._redis.get(key)
            except Exception:
                return None
        return self._memory.get(key)

    def _set_raw(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._redis is not None:
            try:
                self._redis.setex(key, ttl_seconds, value)
                return
            except Exception:
                pass
        self._memory.setex(key, ttl_seconds, value)

    def _delete_raw(self, key: str) -> None:
        if self._redis is not None:
            try:
                self._redis.delete(key)
                return
            except Exception:
                pass
        self._memory.delete(key)

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self._get_raw(key)
        if raw is None:
            return None
        try:
            value = json.loads(raw)
            if isinstance(value, dict):
                return value
            return None
        except Exception:
            return None

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._set_raw(key, json.dumps(value), ttl_seconds)

    def delete(self, key: str) -> None:
        self._delete_raw(key)


cache_client = CacheClient()

