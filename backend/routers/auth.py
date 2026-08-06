"""
Authentication router — JWT-based (v2).

Replaces the old name-only capturista login with:
- POST /api/auth/login  — email + password → JWT
- GET  /api/auth/me     — returns current user from JWT
- require_auth          — FastAPI dependency for protected routes
- require_admin         — FastAPI dependency for admin-only routes
- require_tecnico       — FastAPI dependency for tecnico-or-admin routes
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from pydantic import BaseModel, field_validator

from database import get_db, _DBAdapter
from validators import validate_email_format

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_JWT_SECRET = os.environ.get("JWT_SECRET")
if not _JWT_SECRET or _JWT_SECRET == "dev-secret-change-in-production":
    raise RuntimeError(
        "JWT_SECRET environment variable must be set to a strong secret "
        "(>=32 bytes). The placeholder 'dev-secret-change-in-production' is "
        "not accepted."
    )
if len(_JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 bytes long.")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "8"))

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email_valido(cls, v: str) -> str:
        return validate_email_format(v)


class LoginResponse(BaseModel):
    access_token: str
    rol: str
    nombre: str
    usuario_id: int


class CurrentUser(BaseModel):
    usuario_id: int
    nombre: str
    email: str
    rol: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_jwt(usuario_id: int, rol: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_JWT_EXPIRE_HOURS)
    payload = {"sub": str(usuario_id), "rol": rol, "exp": expire}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _verify_password(plain: str, hashed: str | None) -> bool:
    # A NULL/empty hash (a Pendiente account created via invite, not yet
    # activated) must NEVER authenticate. Return False without invoking bcrypt.
    # Defense-in-depth: the activo=FALSE gate already blocks these users, but
    # this guard protects against a future gate bypass. See spec: NULL Hash
    # Hardening.
    if not hashed:
        return False
    try:
        return _pwd_context.verify(plain, hashed)
    except UnknownHashError:
        return False


def _hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


# ---------------------------------------------------------------------------
# Auth dependencies (shared — import these in other routers)
# ---------------------------------------------------------------------------

def require_auth(
    token: Annotated[str, Depends(_oauth2_scheme)],
    db: Annotated[_DBAdapter, Depends(get_db)],
) -> CurrentUser:
    """Validate JWT and return the current user. Raises 401 on failure."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        usuario_id_str: str | None = payload.get("sub")
        if usuario_id_str is None:
            raise credentials_exc
        usuario_id = int(usuario_id_str)
    except (JWTError, ValueError):
        raise credentials_exc

    row = db.execute(
        "SELECT id, nombre, email, rol, activo FROM usuarios WHERE id = %s",
        (usuario_id,),
    ).fetchone()

    if row is None or not row["activo"]:
        raise credentials_exc

    return CurrentUser(
        usuario_id=row["id"],
        nombre=row["nombre"],
        email=row["email"],
        rol=row["rol"],
    )


def require_admin(
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> CurrentUser:
    """Ensure the current user has the 'admin' role. Raises 403 otherwise."""
    if user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return user


def require_roles(*roles: str):
    """Build a dependency that allows only the provided roles."""
    allowed = set(roles)

    def _require_roles(user: Annotated[CurrentUser, Depends(require_auth)]) -> CurrentUser:
        if user.rol not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta acción",
            )
        return user

    return _require_roles


# ---------------------------------------------------------------------------
# Organization access matrix (single source of truth — Issue #80)
#
# Two scopes drive every org-aware authorization decision:
#   * leadership scope  = the org account owner + registered leaders
#                         (organizaciones_lideres). Plain members are NOT
#                         leaders; they only see org identity/stats.
#   * capture scope      = the org account owner + leaders + members. Any of
#                         these can be the ``usuario_id`` that captured a row.
#
# A user passes the org-leader bypass for a resource iff they are in the
# *leadership* scope of some org whose *capture* scope includes the resource's
# capturer. ``user_leads_org`` and ``user_leads_capturer_org`` are the only
# functions that encode these rules; ``assert_resource_owner`` (here) and
# ``_assert_org_access`` (perfiles.py) both delegate to them.
#
# Leadership source of truth is the ``organizaciones_lideres`` table, never the
# legacy ``organizaciones.lider_usuario_id`` column (see Issue #53).
# ---------------------------------------------------------------------------

def user_leads_org(db: _DBAdapter, user_id: int, org_id: int) -> bool:
    """True if ``user_id`` is the org account owner or a registered leader of
    ``org_id``. Members are intentionally excluded."""
    row = db.execute(
        """
        SELECT 1 FROM organizaciones o
        WHERE o.id = %s
          AND (
                o.usuario_id = %s
                OR EXISTS (
                    SELECT 1 FROM organizaciones_lideres ol
                    WHERE ol.organizacion_id = o.id AND ol.usuario_id = %s
                )
              )
        """,
        (org_id, user_id, user_id),
    ).fetchone()
    return row is not None


def user_leads_capturer_org(db: _DBAdapter, user_id: int, capturer_user_id: int) -> bool:
    """True if ``user_id`` leads (account or leader) an organization whose
    capture scope — account + leaders + members — includes ``capturer_user_id``.

    This is the single rule behind the org-leader bypass shared across modules.
    """
    row = db.execute(
        """
        SELECT 1 FROM organizaciones o
        WHERE (
                o.usuario_id = %s
                OR EXISTS (
                    SELECT 1 FROM organizaciones_lideres ol
                    WHERE ol.organizacion_id = o.id AND ol.usuario_id = %s
                )
              )
          AND (
                o.usuario_id = %s
                OR EXISTS (
                    SELECT 1 FROM organizaciones_lideres ol2
                    WHERE ol2.organizacion_id = o.id AND ol2.usuario_id = %s
                )
                OR EXISTS (
                    SELECT 1 FROM organizaciones_miembros om
                    WHERE om.organizacion_id = o.id AND om.usuario_id = %s
                )
              )
        LIMIT 1
        """,
        (user_id, user_id, capturer_user_id, capturer_user_id, capturer_user_id),
    ).fetchone()
    return row is not None


def assert_resource_owner(
    row_user_id: int,
    user: CurrentUser,
    db: _DBAdapter | None = None,
) -> None:
    """Allow admin access, enforce ownership by usuario_id, or bypass for org leader.

    When ``db`` is provided, the org-leader bypass applies: a user who leads the
    organization whose capture scope includes ``row_user_id`` is granted access.
    The org is derived from the capturer (``row_user_id``), so no estudio id is
    needed.

    Técnico gets the same unrestricted bypass as admin: técnico is a
    read-only, admin-equivalent role that can view every record, and never
    owns a solicitud/estudio itself (write endpoints exclude técnico), so an
    ownership check would only ever reject a técnico reading a legitimate
    record.
    """
    if user.rol in ("admin", "tecnico"):
        return
    if row_user_id == user.usuario_id:
        return

    # Leader bypass: the user leads an org whose capture scope owns this row.
    if db is not None and user_leads_capturer_org(db, user.usuario_id, row_user_id):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tiene permisos para este recurso",
    )


def _assert_case_pair(
    *,
    user: CurrentUser,
    db: _DBAdapter,
    estudio_id: int | None = None,
    solicitud_id: int | None = None,
    beneficiario_id: int | None = None,
) -> tuple[dict, dict | None]:
    """Authorize a case and prove all supplied records share one beneficiary."""
    solicitud = None
    if solicitud_id is not None:
        solicitud = db.execute(
            "SELECT id, usuario_id, beneficiario_id FROM solicitudes_tecnicas WHERE id = %s",
            (solicitud_id,),
        ).fetchone()
        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if estudio_id is not None:
        estudio = db.execute(
            "SELECT id, usuario_id, beneficiario_id FROM estudios_socioeconomicos WHERE id = %s",
            (estudio_id,),
        ).fetchone()
    else:
        lookup_beneficiario_id = beneficiario_id
        if lookup_beneficiario_id is None and solicitud is not None:
            lookup_beneficiario_id = solicitud["beneficiario_id"]
        estudio = db.execute(
            """
            SELECT id, usuario_id, beneficiario_id
            FROM estudios_socioeconomicos
            WHERE beneficiario_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (lookup_beneficiario_id,),
        ).fetchone()

    if estudio is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    case_beneficiario_id = estudio["beneficiario_id"]
    supplied_beneficiario_ids = [
        value
        for value in (
            beneficiario_id,
            solicitud["beneficiario_id"] if solicitud is not None else None,
        )
        if value is not None
    ]
    if any(value != case_beneficiario_id for value in supplied_beneficiario_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los registros no pertenecen al mismo beneficiario",
        )

    assert_resource_owner(estudio["usuario_id"], user, db=db)
    if solicitud is not None:
        assert_resource_owner(solicitud["usuario_id"], user, db=db)
    return dict(estudio), dict(solicitud) if solicitud is not None else None


def require_tecnico_or_admin(
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> CurrentUser:
    """Ensure current user is técnico or admin. Raises 403 otherwise."""
    return require_roles("tecnico", "admin")(user)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Annotated[_DBAdapter, Depends(get_db)]) -> LoginResponse:
    """
    Authenticate with email and password. Returns a JWT access token.
    Uses the same error message for wrong password AND unknown email
    to prevent user enumeration.
    """
    _invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    row = db.execute(
        "SELECT id, nombre, email, rol, password_hash, activo FROM usuarios WHERE email = %s",
        (body.email.lower().strip(),),
    ).fetchone()

    if row is None or not row["activo"]:
        raise _invalid

    if not _verify_password(body.password, row["password_hash"]):
        raise _invalid

    token = _create_jwt(row["id"], row["rol"])

    return LoginResponse(
        access_token=token,
        rol=row["rol"],
        nombre=row["nombre"],
        usuario_id=row["id"],
    )


@router.get("/auth/me", response_model=CurrentUser)
def get_me(user: Annotated[CurrentUser, Depends(require_auth)]) -> CurrentUser:
    """Return the currently authenticated user's profile."""
    return user
