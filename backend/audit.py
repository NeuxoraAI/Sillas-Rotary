"""Helpers for security audit events.

Audit metadata must describe the event without duplicating secrets, bearer
tokens, or full signed URLs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from ipaddress import ip_address
from typing import Any

from fastapi import Request
from psycopg2.extras import Json

from database import _DBAdapter
from routers.auth import CurrentUser


_SENSITIVE_KEY_PARTS = (
    "authorization",
    "bearer",
    "jwt",
    "secret",
    "service_key",
    "token",
)
_URL_KEY_PARTS = ("signed", "url")


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS) or (
        any(part in lowered for part in _URL_KEY_PARTS)
    )


def sanitize_audit_metadata(value: Any) -> Any:
    """Return JSON-safe metadata with secrets and full URLs redacted."""
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            sanitized[key_str] = "[REDACTED]" if _is_sensitive_key(key_str) else sanitize_audit_metadata(item)
        return sanitized

    if isinstance(value, str):
        if value.startswith(("http://", "https://")) or "Bearer " in value:
            return "[REDACTED]"
        return value

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize_audit_metadata(item) for item in value]

    return value


def get_request_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        candidate = forwarded_for.split(",", 1)[0].strip() or None
    else:
        candidate = request.client.host if request.client else None
    if not candidate:
        return None
    try:
        ip_address(candidate)
    except ValueError:
        return None
    return candidate


def registrar_evento(
    db: _DBAdapter,
    *,
    actor: CurrentUser,
    accion: str,
    recurso_tipo: str,
    recurso_id: int | str | None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """Persist a security audit event.

    The helper intentionally redacts metadata defensively before insertion.
    """
    db.execute(
        """
        INSERT INTO auditoria_eventos
            (actor_usuario_id, actor_rol, accion, recurso_tipo, recurso_id, metadata, ip)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            actor.usuario_id,
            actor.rol,
            accion,
            recurso_tipo,
            str(recurso_id) if recurso_id is not None else None,
            Json(sanitize_audit_metadata(metadata or {})),
            get_request_ip(request),
        ),
    )
