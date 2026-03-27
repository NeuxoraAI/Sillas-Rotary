from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from database import get_db

router = APIRouter()


class LoginRequest(BaseModel):
    nombre: str

    @field_validator("nombre")
    @classmethod
    def nombre_min_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v


class LoginResponse(BaseModel):
    capturista_id: int
    nombre: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO capturistas(nombre) VALUES (?)",
            (body.nombre,),
        )
        row = conn.execute(
            "SELECT id, nombre FROM capturistas WHERE nombre = ?",
            (body.nombre,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Error al obtener capturista")

    return LoginResponse(capturista_id=row["id"], nombre=row["nombre"])
