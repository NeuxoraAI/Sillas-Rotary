"""
User management router (v2) — Admin only.

Endpoints:
- POST   /api/usuarios                      — Create a new user (admin)
- GET    /api/usuarios                      — List all users (admin)
- PATCH  /api/usuarios/{id}                 — Edit user fields / reset password (admin)
- DELETE /api/usuarios/{id}                 — Soft deactivate user (admin)
- DELETE /api/usuarios/{id}?permanent=true  — Hard delete user; 409 if referenced (admin)
"""

import logging
from typing import Annotated, Optional

import psycopg2  # noqa: F401  — used for FK violation detection
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, field_validator

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, require_admin, _hash_password
from utils.email import EmailDeliveryError, send_invite
from utils.tokens import INVITE_TTL_SQL, generate_raw_token, hash_token

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_ROLES = {"admin", "capturista", "tecnico", "organizacion"}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UsuarioCreateRequest(BaseModel):
    nombre: str
    email: EmailStr
    # Optional: when omitted (the new default), the user is created passwordless
    # (activo=FALSE, password_hash=NULL) and an invite email is sent so they set
    # their own password. When provided (legacy path), the account is created
    # active with that password — kept for backward compatibility.
    password: Optional[str] = None
    rol: str

    @field_validator("nombre")
    @classmethod
    def nombre_min_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        if v not in _VALID_ROLES:
            raise ValueError(f"El rol debe ser uno de: {', '.join(sorted(_VALID_ROLES))}")
        return v


class UsuarioResponse(BaseModel):
    usuario_id: int
    nombre: str
    email: str
    rol: str
    activo: bool
    organizacion_id: int | None = None
    # True when the account was created via invite and has not been activated
    # yet (activo=FALSE AND password_hash IS NULL). Derived server-side.
    pending: bool = False


class UsuarioUpdateRequest(BaseModel):
    nombre: str | None = None
    email: EmailStr | None = None
    rol: str | None = None
    activo: bool | None = None
    password: str | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _VALID_ROLES:
            raise ValueError(f"El rol debe ser uno de: {', '.join(sorted(_VALID_ROLES))}")
        return v


class UsuarioDeactivateResponse(BaseModel):
    usuario_id: int
    activo: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/usuarios", status_code=status.HTTP_201_CREATED, response_model=UsuarioResponse)
def create_usuario(
    body: UsuarioCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> UsuarioResponse:
    """Create a new user. Admin only."""
    # Check for duplicate email
    existing = db.execute(
        "SELECT id FROM usuarios WHERE email = %s",
        (body.email.lower(),),
    ).fetchone()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        )

    # Two creation paths:
    #  - Legacy (password provided): hash it, account is active immediately.
    #  - Invite (no password): password_hash=NULL, activo=FALSE, then email a
    #    one-time invite link so the user sets their own password (proving email
    #    ownership). The account stays Pendiente until activation.
    invite_flow = body.password is None

    if invite_flow:
        row = db.execute(
            """
            INSERT INTO usuarios (nombre, email, password_hash, rol, activo)
            VALUES (%s, %s, NULL, %s, FALSE)
            RETURNING id, nombre, email, rol, activo
            """,
            (body.nombre.strip(), body.email.lower(), body.rol),
        ).fetchone()
    else:
        password_hash = _hash_password(body.password)
        row = db.execute(
            """
            INSERT INTO usuarios (nombre, email, password_hash, rol)
            VALUES (%s, %s, %s, %s)
            RETURNING id, nombre, email, rol, activo
            """,
            (body.nombre.strip(), body.email.lower(), password_hash, body.rol),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Error al crear el usuario")

    # Invite path: issue a single-use invite token (72h) and email it.
    # Fail-open — if delivery fails the user stays Pendiente and an admin can
    # resend via POST /usuarios/{id}/reenviar-invitacion.
    if invite_flow:
        raw_token = generate_raw_token()
        db.execute(
            f"""
            INSERT INTO password_tokens (usuario_id, token_hash, tipo, expires_at)
            VALUES (%s, %s, 'invite', NOW() + INTERVAL '{INVITE_TTL_SQL}')
            """,
            (row["id"], hash_token(raw_token)),
        )
        try:
            send_invite(row["email"], raw_token)
        except EmailDeliveryError:
            logger.warning(
                "Invite email delivery failed for usuario_id=%s; user remains "
                "Pendiente until an admin resends the invitation.",
                row["id"],
            )

    # If creating an organization user, auto-create the organizaciones entry
    # and add the user as a leader so /api/me/perfil resolves correctly
    if body.rol == "organizacion":
        db.execute(
            """
            INSERT INTO organizaciones (nombre, email, usuario_id)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (body.nombre.strip(), body.email.lower(), row["id"]),
        )
        org_row = db.fetchone()
        db.execute(
            "INSERT INTO organizaciones_lideres (organizacion_id, usuario_id) VALUES (%s, %s)",
            (org_row["id"], row["id"]),
        )

    return UsuarioResponse(
        usuario_id=row["id"],
        nombre=row["nombre"],
        email=row["email"],
        rol=row["rol"],
        activo=row["activo"],
        pending=invite_flow,
    )


@router.get("/usuarios", response_model=list[UsuarioResponse])
def list_usuarios(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> list[UsuarioResponse]:
    """List all users (active and inactive). Admin only."""
    rows = db.execute(
        """
        SELECT u.id, u.nombre, u.email, u.rol, u.activo,
               (u.password_hash IS NULL AND NOT u.activo) AS pending,
               (
                   SELECT MIN(ol.organizacion_id)
                   FROM organizaciones_lideres ol
                   WHERE ol.usuario_id = u.id
               ) AS organizacion_id
        FROM usuarios u
        ORDER BY u.id
        """,
    ).fetchall()

    return [
        UsuarioResponse(
            usuario_id=row["id"],
            nombre=row["nombre"],
            email=row["email"],
            rol=row["rol"],
            activo=row["activo"],
            organizacion_id=row["organizacion_id"],
            pending=row["pending"],
        )
        for row in rows
    ]


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(
    usuario_id: int,
    body: UsuarioUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    admin: Annotated[CurrentUser, Depends(require_admin)],
) -> UsuarioResponse:
    """
    Edit a user's nombre, email, rol, activo, or reset password. Admin only.

    Guards:
    - An admin cannot deactivate their own account (activo=False) via this endpoint.
    - An admin cannot change their own rol away from 'admin'.
    """
    existing = db.execute(
        "SELECT id, nombre, email, rol, activo FROM usuarios WHERE id = %s",
        (usuario_id,),
    ).fetchone()

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    # Self-protection guards
    if usuario_id == admin.usuario_id:
        if body.activo is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede desactivar su propia cuenta",
            )
        if body.rol is not None and body.rol != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede cambiar su propio rol",
            )

    # Validate email uniqueness if changing
    if body.email is not None:
        email_lower = body.email.lower()
        dup = db.execute(
            "SELECT id FROM usuarios WHERE email = %s AND id != %s",
            (email_lower, usuario_id),
        ).fetchone()
        if dup is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado por otro usuario",
            )

    # Build SET clause dynamically
    fields: list[str] = []
    values: list = []

    if body.nombre is not None:
        fields.append("nombre = %s")
        values.append(body.nombre)
    if body.email is not None:
        fields.append("email = %s")
        values.append(body.email.lower())
    if body.rol is not None:
        fields.append("rol = %s")
        values.append(body.rol)
    if body.activo is not None:
        fields.append("activo = %s")
        values.append(body.activo)
    if body.password is not None:
        fields.append("password_hash = %s")
        values.append(_hash_password(body.password))

    if not fields:
        # Nothing to update — return current state
        org = db.execute(
            "SELECT MIN(organizacion_id) AS id FROM organizaciones_lideres WHERE usuario_id = %s",
            (usuario_id,),
        ).fetchone()
        return UsuarioResponse(
            usuario_id=existing["id"],
            nombre=existing["nombre"],
            email=existing["email"],
            rol=existing["rol"],
            activo=existing["activo"],
            organizacion_id=org["id"] if org else None,
        )

    values.append(usuario_id)
    row = db.execute(
        f"UPDATE usuarios SET {', '.join(fields)} WHERE id = %s RETURNING id, nombre, email, rol, activo",
        tuple(values),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Error al actualizar el usuario")

    org = db.execute(
        "SELECT MIN(organizacion_id) AS id FROM organizaciones_lideres WHERE usuario_id = %s",
        (usuario_id,),
    ).fetchone()

    return UsuarioResponse(
        usuario_id=row["id"],
        nombre=row["nombre"],
        email=row["email"],
        rol=row["rol"],
        activo=row["activo"],
        organizacion_id=org["id"] if org else None,
    )


@router.delete("/usuarios/{usuario_id}", response_model=UsuarioDeactivateResponse)
def delete_usuario(
    usuario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    admin: Annotated[CurrentUser, Depends(require_admin)],
    permanent: bool = Query(default=False, description="Hard delete (true) or soft deactivate (false)"),
) -> UsuarioDeactivateResponse:
    """
    Delete or deactivate a user. Admin only.

    - permanent=false (default): soft delete — sets activo=FALSE.
    - permanent=true: hard delete — fails with 409 if the user is referenced
      by estudios or solicitudes (deactivate instead).

    An admin cannot delete their own account.
    """
    if usuario_id == admin.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede eliminar su propia cuenta",
        )

    existing = db.execute(
        "SELECT id FROM usuarios WHERE id = %s",
        (usuario_id,),
    ).fetchone()

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if not permanent:
        # Soft delete
        db.execute(
            "UPDATE usuarios SET activo = FALSE WHERE id = %s",
            (usuario_id,),
        )
        return UsuarioDeactivateResponse(usuario_id=usuario_id, activo=False)

    # Hard delete — check FK references first
    ref_estudio = db.execute(
        "SELECT 1 FROM estudios_socioeconomicos WHERE usuario_id = %s LIMIT 1",
        (usuario_id,),
    ).fetchone()
    ref_solicitud = db.execute(
        "SELECT 1 FROM solicitudes_tecnicas WHERE usuario_id = %s LIMIT 1",
        (usuario_id,),
    ).fetchone()
    ref_organizacion = db.execute(
        "SELECT 1 FROM organizaciones WHERE usuario_id = %s LIMIT 1",
        (usuario_id,),
    ).fetchone()
    ref_proceso = db.execute(
        "SELECT 1 FROM procesos_tecnicos_participantes WHERE usuario_id = %s LIMIT 1",
        (usuario_id,),
    ).fetchone()

    if ref_estudio or ref_solicitud or ref_organizacion or ref_proceso:
        blocking = []
        if ref_estudio:
            blocking.append("estudios socioeconómicos")
        if ref_solicitud:
            blocking.append("solicitudes técnicas")
        if ref_organizacion:
            blocking.append("organización")
        if ref_proceso:
            blocking.append("procesos técnicos")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El usuario tiene {', '.join(blocking)} asociados; "
                "desactívelo en su lugar para retirarle el acceso."
            ),
        )

    try:
        db.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
    except Exception as exc:
        exc_str = str(exc)
        if "foreign key" in exc_str.lower() or "violates" in exc_str.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Este usuario tiene registros asociados y no puede eliminarse permanentemente. "
                    "Desactívelo en su lugar para retirarle el acceso."
                ),
            ) from exc
        raise

    return UsuarioDeactivateResponse(usuario_id=usuario_id, activo=False)
