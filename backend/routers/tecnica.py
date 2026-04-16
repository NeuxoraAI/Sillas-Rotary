import os
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from supabase import create_client

from database import get_db

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_BUCKET = "fotos-tecnica"


def _storage():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    ).storage.from_(_BUCKET)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SolicitudCreateRequest(BaseModel):
    capturista_id: int
    beneficiario_id: int
    entorno: str
    control_tronco: str
    control_cabeza: str
    observaciones_posturales: Optional[str] = None
    altura_total_in: Optional[float] = None
    peso_kg: Optional[float] = None
    medida_cabeza_asiento: Optional[float] = None
    medida_hombro_asiento: Optional[float] = None
    medida_prof_asiento: Optional[float] = None
    medida_rodilla_talon: Optional[float] = None
    medida_ancho_cadera: Optional[float] = None
    foto_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
    status: str = "borrador"

    @field_validator("altura_total_in", "peso_kg", "medida_cabeza_asiento",
                     "medida_hombro_asiento", "medida_prof_asiento",
                     "medida_rodilla_talon", "medida_ancho_cadera")
    @classmethod
    def medida_positiva(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("La medida debe ser mayor que 0")
        return v

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: str) -> str:
        if v not in ("borrador", "completo"):
            raise ValueError("status debe ser 'borrador' o 'completo'")
        return v

    @field_validator("prioridad")
    @classmethod
    def prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Alta", "Media"):
            raise ValueError("prioridad debe ser 'Alta' o 'Media'")
        return v


class SolicitudCreateResponse(BaseModel):
    solicitud_id: int
    beneficiario_id: int
    status: str


class SolicitudUpdateRequest(BaseModel):
    entorno: Optional[str] = None
    control_tronco: Optional[str] = None
    control_cabeza: Optional[str] = None
    observaciones_posturales: Optional[str] = None
    altura_total_in: Optional[float] = None
    peso_kg: Optional[float] = None
    medida_cabeza_asiento: Optional[float] = None
    medida_hombro_asiento: Optional[float] = None
    medida_prof_asiento: Optional[float] = None
    medida_rodilla_talon: Optional[float] = None
    medida_ancho_cadera: Optional[float] = None
    foto_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("borrador", "completo"):
            raise ValueError("status debe ser 'borrador' o 'completo'")
        return v

    @field_validator("prioridad")
    @classmethod
    def prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Alta", "Media"):
            raise ValueError("prioridad debe ser 'Alta' o 'Media'")
        return v


class SolicitudUpdateResponse(BaseModel):
    solicitud_id: int
    status: str
    updated_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload-foto")
async def upload_foto(foto: UploadFile = File(...)) -> dict:
    if foto.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    _, ext = os.path.splitext(foto.filename or "")
    if ext.lower() not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    data = await foto.read()
    if len(data) > _MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="El archivo excede 10MB")

    filename = str(uuid.uuid4()) + ext.lower()

    try:
        _storage().upload(
            path=filename,
            file=data,
            file_options={"content-type": foto.content_type},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error al subir la imagen") from exc

    public_url = _storage().get_public_url(filename)
    return {"foto_url": public_url}


@router.post("/solicitudes", status_code=201, response_model=SolicitudCreateResponse)
def crear_solicitud(body: SolicitudCreateRequest) -> SolicitudCreateResponse:
    with get_db() as conn:
        try:
            solicitud_id = conn.execute(
                """
                INSERT INTO solicitudes_tecnicas
                    (beneficiario_id, capturista_id, entorno, control_tronco, control_cabeza,
                     observaciones_posturales, altura_total_in, peso_kg,
                     medida_cabeza_asiento, medida_hombro_asiento, medida_prof_asiento,
                     medida_rodilla_talon, medida_ancho_cadera, foto_url,
                     entidad_solicitante, prioridad, justificacion, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    body.beneficiario_id,
                    body.capturista_id,
                    body.entorno,
                    body.control_tronco,
                    body.control_cabeza,
                    body.observaciones_posturales,
                    body.altura_total_in,
                    body.peso_kg,
                    body.medida_cabeza_asiento,
                    body.medida_hombro_asiento,
                    body.medida_prof_asiento,
                    body.medida_rodilla_talon,
                    body.medida_ancho_cadera,
                    body.foto_url,
                    body.entidad_solicitante,
                    body.prioridad,
                    body.justificacion,
                    body.status,
                ),
            ).fetchone()["id"]
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Datos de solicitud inválidos") from exc

    return SolicitudCreateResponse(
        solicitud_id=solicitud_id,
        beneficiario_id=body.beneficiario_id,
        status=body.status,
    )


@router.get("/solicitudes/{id}")
def obtener_solicitud(id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM solicitudes_tecnicas WHERE id = %s", (id,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    return dict(row)


@router.patch("/solicitudes/{id}", response_model=SolicitudUpdateResponse)
def actualizar_solicitud(id: int, body: SolicitudUpdateRequest) -> SolicitudUpdateResponse:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM solicitudes_tecnicas WHERE id = %s", (id,)
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        fields = body.model_dump(exclude_none=True)
        if not fields:
            row = conn.execute(
                "SELECT id, status, updated_at FROM solicitudes_tecnicas WHERE id = %s",
                (id,),
            ).fetchone()
            return SolicitudUpdateResponse(
                solicitud_id=row["id"],
                status=row["status"],
                updated_at=row["updated_at"].isoformat(),
            )

        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values())
        values.append(id)

        conn.execute(
            f"UPDATE solicitudes_tecnicas SET {set_clause}, updated_at = NOW() WHERE id = %s",
            values,
        )

        row = conn.execute(
            "SELECT id, status, updated_at FROM solicitudes_tecnicas WHERE id = %s",
            (id,),
        ).fetchone()

    return SolicitudUpdateResponse(
        solicitud_id=row["id"],
        status=row["status"],
        updated_at=row["updated_at"].isoformat(),
    )
