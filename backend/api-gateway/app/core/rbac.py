from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from fastapi import Header

from app.config import settings
from app.core.errors import ValidationError


class Role(str, Enum):
    banker = "banker"
    ops_admin = "ops_admin"
    system_service = "system_service"


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    actor_role: Role


def _parse_role(raw_role: str) -> Role:
    try:
        return Role(raw_role.strip().lower())
    except Exception as exc:
        raise ValidationError(
            code="RBAC_INVALID_ROLE",
            message=f"Unsupported actor role: {raw_role}",
            status_code=403,
            retryable=False,
        ) from exc


def _resolve_actor_context(
    *,
    x_actor_id: str | None,
    x_actor_role: str | None,
) -> ActorContext:
    if not settings.rbac_enforced:
        return ActorContext(
            actor_id=x_actor_id or "system-default",
            actor_role=_parse_role(x_actor_role or "system_service"),
        )

    if not x_actor_id or not x_actor_id.strip():
        raise ValidationError(
            code="RBAC_MISSING_ACTOR_ID",
            message="X-Actor-Id header is required",
            status_code=401,
            retryable=False,
        )
    if not x_actor_role or not x_actor_role.strip():
        raise ValidationError(
            code="RBAC_MISSING_ROLE",
            message="X-Actor-Role header is required",
            status_code=401,
            retryable=False,
        )
    return ActorContext(actor_id=x_actor_id.strip(), actor_role=_parse_role(x_actor_role))


def require_roles(allowed_roles: Iterable[Role]):
    allowed_set = {role for role in allowed_roles}

    def _dependency(
        x_actor_id: str | None = Header(default=None, alias="X-Actor-Id"),
        x_actor_role: str | None = Header(default=None, alias="X-Actor-Role"),
    ) -> ActorContext:
        actor = _resolve_actor_context(x_actor_id=x_actor_id, x_actor_role=x_actor_role)
        if actor.actor_role not in allowed_set:
            raise ValidationError(
                code="RBAC_FORBIDDEN",
                message=f"Role '{actor.actor_role.value}' not allowed for this action",
                status_code=403,
                retryable=False,
            )
        return actor

    return _dependency

