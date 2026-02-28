from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.core.request_context import get_application_id, get_correlation_id


LOGGER_NAME = "orbital_credit.api_gateway"
SERVICE_NAME = "api-gateway"
MOBILE_RE = re.compile(r"^\+91\d{10}$")


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        if MOBILE_RE.match(value):
            return f"{value[:3]}XXXXXX{value[-4:]}"
        return value
    if isinstance(value, float):
        return round(value, 4)
    return value


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = redact_value(payload)
    if not isinstance(redacted, dict):
        return {}
    gps = redacted.get("gps_coordinates")
    if isinstance(gps, dict):
        if "latitude" in gps and isinstance(gps["latitude"], (float, int)):
            gps["latitude"] = round(float(gps["latitude"]), 2)
        if "longitude" in gps and isinstance(gps["longitude"], (float, int)):
            gps["longitude"] = round(float(gps["longitude"]), 2)
    for field in ("name", "farmer_name", "reference_name"):
        if field in redacted and isinstance(redacted[field], str):
            digest = hashlib.sha256(redacted[field].encode("utf-8")).hexdigest()[:12]
            redacted[field] = f"sha256:{digest}"
    return redacted


def log_event(
    *,
    event: str,
    level: str = "INFO",
    application_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    logger = configure_logging()
    final_application_id = application_id or get_application_id()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "correlation_id": get_correlation_id(),
        "application_id": final_application_id,
        "service": SERVICE_NAME,
        "event": event,
    }
    if payload:
        record["payload"] = redact_payload(payload)
    logger.info(json.dumps(record, separators=(",", ":"), default=str))
