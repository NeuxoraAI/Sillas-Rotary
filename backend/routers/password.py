"""
Password / token flows router (v2).

All token-redemption flows and the authenticated change-password endpoint live
here (see design ADR-1), mounted under /api in main.py:

- POST /api/usuarios/{id}/reenviar-invitacion  — admin resends an invite (204)
- POST /api/auth/forgot-password                — public, enumeration-safe (200)
- POST /api/auth/set-password                   — public, invite activation (200)
- POST /api/auth/reset-password                 — public, reset for active user (200)
- POST /api/me/password                         — authenticated change password (204)

Token mechanics (see utils/tokens.py):
  - raw token = secrets.token_urlsafe(32); only its sha256 hex is stored.
  - single-use (used_at stamped on redemption), typed (tipo invite|reset),
    time-bound (invite 72h, reset 1h). Lookups always filter by exact hash,
    tipo, used_at IS NULL and expires_at > NOW().
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

from database import get_db, _DBAdapter
from routers.auth import (
    CurrentUser,
    require_admin,
    require_auth,
    _hash_password,
    _verify_password,
)
from utils.email import EmailDeliveryError, send_invite, send_reset
from utils.tokens import (
    INVITE_TTL_SQL,
    RESET_TTL_SQL,
    generate_raw_token,
    hash_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_GENERIC_FORGOT_MESSAGE = "Si el email existe, recibirás instrucciones en breve."


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

def _validate_min_8(v: str) -> str:
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class TokenPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        return _validate_min_8(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        return _validate_min_8(v)


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _issue_token(db: _DBAdapter, usuario_id: int, tipo: str, ttl_sql: str) -> str:
    """Invalidate prior active tokens of the same (usuario_id, tipo), then insert
    a fresh one. Returns the raw token (only its hash is stored)."""
    db.execute(
        """
        UPDATE password_tokens SET used_at = NOW()
        WHERE usuario_id = %s AND tipo = %s AND used_at IS NULL
        """,
        (usuario_id, tipo),
    )
    raw_token = generate_raw_token()
    db.execute(
        f"""
        INSERT INTO password_tokens (usuario_id, token_hash, tipo, expires_at)
        VALUES (%s, %s, %s, NOW() + INTERVAL '{ttl_sql}')
        """,
        (usuario_id, hash_token(raw_token), tipo),
    )
    return raw_token


def _redeem_token(db: _DBAdapter, token: str, tipo: str) -> dict:
    """Atomically consume a valid, unused, non-expired token of the given tipo
    (single UPDATE avoids a select-then-update race on concurrent redemption).
    Returns the token row (with usuario_id). Raises 400 when
    invalid/expired/used/wrong-tipo."""
    row = db.execute(
        """
        UPDATE password_tokens SET used_at = NOW()
        WHERE token_hash = %s AND tipo = %s
          AND used_at IS NULL AND expires_at > NOW()
        RETURNING id, usuario_id
        """,
        (hash_token(token), tipo),
    ).fetchone()
    if row is None:
        if tipo == "invite":
            detail = (
                "El enlace es inválido o ha expirado. Solicitá una nueva "
                "invitación al administrador."
            )
        else:
            detail = (
                "El enlace es inválido o ha expirado. Solicitá un nuevo enlace "
                "desde la pantalla de inicio de sesión."
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return row


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/usuarios/{usuario_id}/reenviar-invitacion",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reenviar_invitacion(
    usuario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> None:
    """Resend an invite for a Pendiente user (activo=FALSE, password_hash NULL).
    Admin only. Fail-open on email delivery."""
    user = db.execute(
        "SELECT id, nombre, email, activo, password_hash FROM usuarios WHERE id = %s",
        (usuario_id,),
    ).fetchone()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )
    if user["activo"] or user["password_hash"] is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El usuario ya está activo."
        )

    raw_token = _issue_token(db, usuario_id, "invite", INVITE_TTL_SQL)
    try:
        send_invite(user["email"], raw_token, user["nombre"])
    except EmailDeliveryError:
        logger.warning(
            "Invite resend email delivery failed for usuario_id=%s; user remains "
            "Pendiente.",
            usuario_id,
        )
    return None


@router.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
) -> MessageResponse:
    """Enumeration-safe: always returns the same 200 message. A reset token is
    issued and emailed ONLY for an existing active user."""
    user = db.execute(
        "SELECT id, email, activo FROM usuarios WHERE email = %s",
        (body.email.lower().strip(),),
    ).fetchone()

    if user is not None and user["activo"]:
        raw_token = _issue_token(db, user["id"], "reset", RESET_TTL_SQL)
        try:
            send_reset(user["email"], raw_token)
        except EmailDeliveryError:
            logger.warning(
                "Reset email delivery failed for usuario_id=%s.", user["id"]
            )

    return MessageResponse(message=_GENERIC_FORGOT_MESSAGE)


@router.post("/auth/set-password", response_model=MessageResponse)
def set_password(
    body: TokenPasswordRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
) -> MessageResponse:
    """Activate a Pendiente account via a valid invite token: set the password
    (bcrypt) and activo=TRUE, then consume the token."""
    token_row = _redeem_token(db, body.token, "invite")

    # Guard: the token must belong to a still-Pendiente account. A user who was
    # later given a password / deactivated cannot be re-activated via an old
    # invite link.
    user = db.execute(
        "SELECT id, activo, password_hash FROM usuarios WHERE id = %s",
        (token_row["usuario_id"],),
    ).fetchone()
    if user is None or user["activo"] or user["password_hash"] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta deshabilitada. Contactá al administrador.",
        )

    db.execute(
        "UPDATE usuarios SET password_hash = %s, activo = TRUE WHERE id = %s",
        (_hash_password(body.password), token_row["usuario_id"]),
    )
    return MessageResponse(message="Contraseña establecida. Ya podés iniciar sesión.")


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(
    body: TokenPasswordRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
) -> MessageResponse:
    """Reset the password of an active user via a valid reset token. Does NOT
    change activo."""
    token_row = _redeem_token(db, body.token, "reset")

    db.execute(
        "UPDATE usuarios SET password_hash = %s WHERE id = %s",
        (_hash_password(body.password), token_row["usuario_id"]),
    )
    return MessageResponse(message="Contraseña actualizada. Ya podés iniciar sesión.")


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> None:
    """Authenticated password change for any of the 4 roles. Verifies the
    current password before applying the change."""
    row = db.execute(
        "SELECT password_hash FROM usuarios WHERE id = %s",
        (user.usuario_id,),
    ).fetchone()

    if row is None or row["password_hash"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu cuenta aún no tiene contraseña establecida. Usá el enlace de invitación.",
        )

    if not _verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )

    db.execute(
        "UPDATE usuarios SET password_hash = %s WHERE id = %s",
        (_hash_password(body.new_password), user.usuario_id),
    )
    return None
