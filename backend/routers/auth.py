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
from pydantic import BaseModel, EmailStr

from database import get_db, _DBAdapter

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


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


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


def require_tecnico_or_admin(
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> CurrentUser:
    """Ensure current user is técnico or admin. Raises 403 otherwise."""
    if user.rol not in ("tecnico", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de técnico o administrador",
        )
    return user


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
