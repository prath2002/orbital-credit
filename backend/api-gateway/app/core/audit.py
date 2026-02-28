from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_event, redact_payload
from app.core.request_context import get_correlation_id
from app.models import AuditEvent


def emit_audit_event(
    *,
    db: Session,
    event: str,
    actor_type: str,
    actor_id: str,
    application_id: UUID | None,
    payload: dict[str, Any] | None = None,
) -> None:
    event_payload: dict[str, Any] = payload.copy() if payload else {}
    event_payload["correlation_id"] = get_correlation_id()
    db.add(
        AuditEvent(
            application_id=application_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event,
            payload_json=event_payload,
        )
    )
    log_event(
        event=f"audit_{event}",
        application_id=str(application_id) if application_id else None,
        payload=redact_payload(event_payload),
    )
