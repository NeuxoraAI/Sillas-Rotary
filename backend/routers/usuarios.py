"""
User management router (v2) — Admin only.

Endpoints:
- POST   /api/usuarios           — Create a new user (admin)
- GET    /api/usuarios           — List all users (admin)
- DELETE /api/usuarios/{id}      — Deactivate user (admin, soft delete)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, require_admin, _hash_password

router = APIRouter()

_VALID_ROLES = {"admin", "capturista", "tecnico"}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UsuarioCreateRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str
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
    def password_min_length(cls, v: str) -> str:
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

    return UsuarioResponse(
        usuario_id=row["id"],
        nombre=row["nombre"],
        email=row["email"],
        rol=row["rol"],
        activo=row["activo"],
    )


@router.get("/usuarios", response_model=list[UsuarioResponse])
def list_usuarios(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> list[UsuarioResponse]:
    """List all users (active and inactive). Admin only."""
    rows = db.execute(
        "SELECT id, nombre, email, rol, activo FROM usuarios ORDER BY id"
    ).fetchall()

    return [
        UsuarioResponse(
            usuario_id=row["id"],
            nombre=row["nombre"],
            email=row["email"],
            rol=row["rol"],
            activo=row["activo"],
        )
        for row in rows
    ]


@router.delete("/usuarios/{usuario_id}", response_model=UsuarioDeactivateResponse)
def deactivate_usuario(
    usuario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> UsuarioDeactivateResponse:
    """Soft-delete a user by setting activo=false. Admin only."""
    existing = db.execute(
        "SELECT id FROM usuarios WHERE id = %s",
        (usuario_id,),
    ).fetchone()

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    db.execute(
        "UPDATE usuarios SET activo = FALSE WHERE id = %s",
        (usuario_id,),
    )

    return UsuarioDeactivateResponse(usuario_id=usuario_id, activo=False)
