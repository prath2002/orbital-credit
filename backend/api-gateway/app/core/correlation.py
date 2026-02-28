from __future__ import annotations

import uuid
from collections.abc import Callable
from time import perf_counter

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.core.logging import log_event
from app.core.request_context import set_application_id, set_correlation_id


CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> StarletteResponse:
        correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        start = perf_counter()
        request.state.correlation_id = correlation_id
        set_correlation_id(correlation_id)
        set_application_id(None)

        try:
            response = await call_next(request)
            duration_ms = round((perf_counter() - start) * 1000, 2)
            log_event(
                event="request_completed",
                payload={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            response.headers[CORRELATION_HEADER] = correlation_id
            return response
        except Exception:
            duration_ms = round((perf_counter() - start) * 1000, 2)
            log_event(
                level="ERROR",
                event="request_failed",
                payload={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            set_correlation_id(None)
            set_application_id(None)
