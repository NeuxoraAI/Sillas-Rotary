import os
import uuid
from decimal import Decimal
from urllib.parse import urlparse, unquote
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator, model_validator, ValidationInfo
from supabase import create_client

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, assert_resource_owner, require_roles
from validators import (
    validate_observaciones_posturales,
    validate_medida_tecnica,
    validate_entidad_solicitante,
    validate_justificacion,
    validate_entorno,
    validate_control_tronco,
    validate_control_cabeza,
    validate_unidad_medida,
    validate_prioridad,
    validate_status,
)

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_BUCKET = "fotos-tecnica"
_SIGNED_URL_TTL_SECONDS = 60
_STORAGE_URL_PREFIX = f"storage://{_BUCKET}/"


class DatabaseError(Exception):
    """Raised when a database operation fails for a known reason."""
    pass


class ForeignKeyViolationError(DatabaseError):
    """Raised when a foreign key constraint is violated."""
    pass


class CheckViolationError(DatabaseError):
    """Raised when a check constraint is violated."""
    pass


def _classify_db_error(exc: Exception) -> HTTPException:
    """Classify a database error into a structured HTTPException.

    psycopg2 raises IntegrityError for FK and check violations.
    We inspect the exception to produce deterministic, structured 4xx responses
    instead of a generic 400 catch-all.
    """
    exc_repr = str(exc).lower()

    # Foreign key violations (e.g. beneficiario_id references a non-existent row)
    if "foreign key" in exc_repr or "violates foreign key" in exc_repr:
        return HTTPException(
            status_code=422,
            detail={
                "type": "foreign_key_violation",
                "message": "El recurso referenciado no existe",
            },
        )

    # Check constraint violations (e.g. invalid enum values, negative measures)
    if "check constraint" in exc_repr or "violates check" in exc_repr:
        return HTTPException(
            status_code=422,
            detail={
                "type": "constraint_violation",
                "message": "Uno o más valores no cumplen las restricciones de la base de datos",
            },
        )

    # Not-null violations
    if "not null" in exc_repr or "violates not-null" in exc_repr:
        return HTTPException(
            status_code=422,
            detail={
                "type": "constraint_violation",
                "message": "Falta un campo obligatorio",
            },
        )

    # Unique constraint violations
    if "unique" in exc_repr or "duplicate key" in exc_repr:
        return HTTPException(
            status_code=409,
            detail={
                "type": "unique_violation",
                "message": "El registro ya existe",
            },
        )

    # Fallthrough: unknown DB error — return 500, not 400
    return HTTPException(
        status_code=500,
        detail="Error interno de base de datos",
    )


def _storage():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    ).storage.from_(_BUCKET)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SolicitudCreateRequest(BaseModel):
    beneficiario_id: int
    entorno: str
    control_tronco: str
    control_cabeza: str
    observaciones_posturales: Optional[str] = None
    unidad_medida: str = "in"
    altura_total_in: Optional[Decimal] = None
    peso_kg: Optional[Decimal] = None
    medida_cabeza_asiento: Optional[Decimal] = None
    medida_hombro_asiento: Optional[Decimal] = None
    medida_prof_asiento: Optional[Decimal] = None
    medida_rodilla_talon: Optional[Decimal] = None
    medida_ancho_cadera: Optional[Decimal] = None
    foto_path: Optional[str] = None
    foto_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
    status: str = "borrador"

    @field_validator("altura_total_in", "peso_kg", "medida_cabeza_asiento",
                     "medida_hombro_asiento", "medida_prof_asiento",
                     "medida_rodilla_talon", "medida_ancho_cadera", mode="before")
    @classmethod
    def validate_medida_field(cls, v, info: ValidationInfo) -> Optional[Decimal]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_medida_tecnica(str(v), info.field_name)

    @field_validator("observaciones_posturales", mode="before")
    @classmethod
    def validate_obs_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_observaciones_posturales(str(v))

    @field_validator("entidad_solicitante", mode="before")
    @classmethod
    def validate_entidad_solicitante_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_entidad_solicitante(str(v))

    @field_validator("justificacion", mode="before")
    @classmethod
    def validate_justificacion_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_justificacion(str(v))

    @field_validator("entorno")
    @classmethod
    def _entorno_valido(cls, v: str) -> str:
        return validate_entorno(v)

    @field_validator("control_tronco")
    @classmethod
    def _control_tronco_valido(cls, v: str) -> str:
        return validate_control_tronco(v)

    @field_validator("control_cabeza")
    @classmethod
    def _control_cabeza_valido(cls, v: str) -> str:
        return validate_control_cabeza(v)

    @field_validator("unidad_medida")
    @classmethod
    def _unidad_valida(cls, v: str) -> str:
        return validate_unidad_medida(v)

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: str) -> str:
        return validate_status(v)

    @field_validator("prioridad")
    @classmethod
    def _prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_prioridad(v)

    @model_validator(mode="after")
    def _validar_completo_t1(self):
        if self.status != "completo":
            return self

        missing: list[str] = []

        medidas = {
            "altura_total_in": self.altura_total_in,
            "peso_kg": self.peso_kg,
            "medida_cabeza_asiento": self.medida_cabeza_asiento,
            "medida_hombro_asiento": self.medida_hombro_asiento,
            "medida_prof_asiento": self.medida_prof_asiento,
            "medida_rodilla_talon": self.medida_rodilla_talon,
            "medida_ancho_cadera": self.medida_ancho_cadera,
        }
        for field_name, value in medidas.items():
            if value is None:
                missing.append(field_name)

        if missing:
            raise ValueError(
                f"{', '.join(missing)} es obligatorio cuando status es completo"
            )

        return self


class SolicitudCreateResponse(BaseModel):
    solicitud_id: int
    beneficiario_id: int
    status: str


class SolicitudUpdateRequest(BaseModel):
    entorno: Optional[str] = None
    control_tronco: Optional[str] = None
    control_cabeza: Optional[str] = None
    observaciones_posturales: Optional[str] = None
    unidad_medida: Optional[str] = None
    altura_total_in: Optional[Decimal] = None
    peso_kg: Optional[Decimal] = None
    medida_cabeza_asiento: Optional[Decimal] = None
    medida_hombro_asiento: Optional[Decimal] = None
    medida_prof_asiento: Optional[Decimal] = None
    medida_rodilla_talon: Optional[Decimal] = None
    medida_ancho_cadera: Optional[Decimal] = None
    foto_path: Optional[str] = None
    foto_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
    status: Optional[str] = None

    @field_validator("altura_total_in", "peso_kg", "medida_cabeza_asiento",
                     "medida_hombro_asiento", "medida_prof_asiento",
                     "medida_rodilla_talon", "medida_ancho_cadera", mode="before")
    @classmethod
    def validate_medida_field(cls, v, info: ValidationInfo) -> Optional[Decimal]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_medida_tecnica(str(v), info.field_name)

    @field_validator("observaciones_posturales", mode="before")
    @classmethod
    def validate_obs_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_observaciones_posturales(str(v))

    @field_validator("entidad_solicitante", mode="before")
    @classmethod
    def validate_entidad_solicitante_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_entidad_solicitante(str(v))

    @field_validator("justificacion", mode="before")
    @classmethod
    def validate_justificacion_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_justificacion(str(v))

    @field_validator("entorno")
    @classmethod
    def _entorno_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_entorno(v)

    @field_validator("control_tronco")
    @classmethod
    def _control_tronco_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_control_tronco(v)

    @field_validator("control_cabeza")
    @classmethod
    def _control_cabeza_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_control_cabeza(v)

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_status(v)

    @field_validator("unidad_medida")
    @classmethod
    def _unidad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_unidad_medida(v)

    @field_validator("prioridad")
    @classmethod
    def _prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_prioridad(v)

    @model_validator(mode="after")
    def _validar_completo_t2(self):
        if self.status != "completo":
            return self

        missing: list[str] = []

        medidas = {
            "altura_total_in": self.altura_total_in,
            "peso_kg": self.peso_kg,
            "medida_cabeza_asiento": self.medida_cabeza_asiento,
            "medida_hombro_asiento": self.medida_hombro_asiento,
            "medida_prof_asiento": self.medida_prof_asiento,
            "medida_rodilla_talon": self.medida_rodilla_talon,
            "medida_ancho_cadera": self.medida_ancho_cadera,
        }
        for field_name, value in medidas.items():
            if value is None:
                missing.append(field_name)

        if missing:
            raise ValueError(
                f"{', '.join(missing)} es obligatorio cuando status es completo"
            )

        return self


class SolicitudUpdateResponse(BaseModel):
    solicitud_id: int
    status: str
    updated_at: str


def extract_foto_path(raw_value: Optional[str]) -> Optional[str]:
    if raw_value is None:
        return None

    value = raw_value.strip()
    if not value:
        return None

    if value.startswith(_STORAGE_URL_PREFIX):
        path = value[len(_STORAGE_URL_PREFIX):]
        return path.strip("/") or None

    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        marker = f"/{_BUCKET}/"
        if marker in parsed.path:
            return unquote(parsed.path.split(marker, 1)[1].strip("/")) or None
        return None

    return value.strip("/") or None


def _derive_legacy_foto_url(foto_path: Optional[str]) -> Optional[str]:
    if foto_path is None:
        return None
    return f"{_STORAGE_URL_PREFIX}{foto_path}"


def _resolve_foto_refs(*, foto_path: Optional[str], foto_url: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    canonical_path = extract_foto_path(foto_path) or extract_foto_path(foto_url)
    derived_url = _derive_legacy_foto_url(canonical_path)
    return canonical_path, derived_url


def _signed_url_from_response(raw_response: object) -> Optional[str]:
    if isinstance(raw_response, str):
        return raw_response

    if isinstance(raw_response, dict):
        candidate = (
            raw_response.get("signedURL")
            or raw_response.get("signedUrl")
            or raw_response.get("signed_url")
            or raw_response.get("url")
        )
        if isinstance(candidate, str):
            return candidate

    return None


def _try_backfill_foto_path(
    db: _DBAdapter,
    *,
    solicitud_id: int,
    foto_path: Optional[str],
    foto_url: Optional[str],
) -> None:
    if foto_path is None:
        return
    try:
        db.execute(
            """
            UPDATE solicitudes_tecnicas
            SET foto_path = %s, foto_url = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (foto_path, foto_url, solicitud_id),
        )
    except Exception:
        # Compatibilidad temporal: si aún no existe la columna en un entorno
        # viejo, mantenemos el flujo v2 sin romper solicitudes.
        return


def _load_solicitud_for_foto(db: _DBAdapter, solicitud_id: int) -> Optional[dict]:
    try:
        row = db.execute(
            """
            SELECT id, usuario_id, foto_path, foto_url
            FROM solicitudes_tecnicas
            WHERE id = %s
            """,
            (solicitud_id,),
        ).fetchone()
        if row is not None:
            return dict(row)
    except Exception:
        pass

    legacy = db.execute(
        "SELECT id, usuario_id, foto_url FROM solicitudes_tecnicas WHERE id = %s",
        (solicitud_id,),
    ).fetchone()
    if legacy is None:
        return None
    row = dict(legacy)
    row["foto_path"] = None
    return row


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload-foto")
async def upload_foto(
    foto: UploadFile = File(...),
    _usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin"))] = None,
) -> dict:
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

    return {
        "foto_path": filename,
        "foto_url": _derive_legacy_foto_url(filename),
    }


@router.post("/solicitudes", status_code=201, response_model=SolicitudCreateResponse)
def crear_solicitud(
    body: SolicitudCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin"))],
) -> SolicitudCreateResponse:
    body = _normalize_medidas(body)
    resolved_foto_path, resolved_foto_url = _resolve_foto_refs(
        foto_path=body.foto_path,
        foto_url=body.foto_url,
    )

    try:
        solicitud_id = db.execute(
            """
            INSERT INTO solicitudes_tecnicas
                (beneficiario_id, usuario_id, entorno, control_tronco, control_cabeza,
                 observaciones_posturales, altura_total_in, peso_kg,
                 medida_cabeza_asiento, medida_hombro_asiento, medida_prof_asiento,
                 medida_rodilla_talon, medida_ancho_cadera, unidad_captura, foto_url,
                 entidad_solicitante, prioridad, justificacion, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.beneficiario_id,
                usuario.usuario_id,
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
                body.unidad_medida,
                resolved_foto_url,
                body.entidad_solicitante,
                body.prioridad,
                body.justificacion,
                body.status,
            ),
        ).fetchone()["id"]
    except Exception as exc:
        raise _classify_db_error(exc) from exc

    _try_backfill_foto_path(
        db,
        solicitud_id=solicitud_id,
        foto_path=resolved_foto_path,
        foto_url=resolved_foto_url,
    )

    return SolicitudCreateResponse(
        solicitud_id=solicitud_id,
        beneficiario_id=body.beneficiario_id,
        status=body.status,
    )


@router.get("/solicitudes/{id}")
def obtener_solicitud(
    id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin"))],
) -> dict:
    row = db.execute(
        "SELECT * FROM solicitudes_tecnicas WHERE id = %s", (id,)
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    assert_resource_owner(row["usuario_id"], usuario)

    return dict(row)


@router.patch("/solicitudes/{id}", response_model=SolicitudUpdateResponse)
def actualizar_solicitud(
    id: int,
    body: SolicitudUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin"))],
) -> SolicitudUpdateResponse:
    existing = db.execute(
        "SELECT id, usuario_id FROM solicitudes_tecnicas WHERE id = %s", (id,)
    ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    assert_resource_owner(existing["usuario_id"], usuario)

    fields = body.model_dump(exclude_none=True)
    if fields.get("unidad_medida") in ("cm", "in"):
        fields = _normalize_medidas_patch(fields)
    # Rename to DB column name
    if "unidad_medida" in fields:
        fields["unidad_captura"] = fields.pop("unidad_medida")

    resolved_foto_path, resolved_foto_url = _resolve_foto_refs(
        foto_path=fields.pop("foto_path", None),
        foto_url=fields.get("foto_url"),
    )
    if resolved_foto_url is not None:
        fields["foto_url"] = resolved_foto_url

    if not fields:
        row = db.execute(
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

    db.execute(
        f"UPDATE solicitudes_tecnicas SET {set_clause}, updated_at = NOW() WHERE id = %s",
        values,
    )

    _try_backfill_foto_path(
        db,
        solicitud_id=id,
        foto_path=resolved_foto_path,
        foto_url=resolved_foto_url,
    )

    row = db.execute(
        "SELECT id, status, updated_at FROM solicitudes_tecnicas WHERE id = %s",
        (id,),
    ).fetchone()

    return SolicitudUpdateResponse(
        solicitud_id=row["id"],
        status=row["status"],
        updated_at=row["updated_at"].isoformat(),
    )


def _to_inches(v: Optional[Decimal], unidad: str) -> Optional[Decimal]:
    if v is None:
        return None
    if unidad == "cm":
        # cm to inches: divide by 2.54, round to 3 decimal places
        inches = v / Decimal("2.54")
        return inches.quantize(Decimal("0.001"))
    return v


def _normalize_medidas(body: SolicitudCreateRequest) -> SolicitudCreateRequest:
    data = body.model_dump()
    unidad = data.get("unidad_medida", "in")
    for key in ("altura_total_in", "medida_cabeza_asiento", "medida_hombro_asiento", "medida_prof_asiento", "medida_rodilla_talon", "medida_ancho_cadera"):
        data[key] = _to_inches(data.get(key), unidad)
    return SolicitudCreateRequest(**data)


def _normalize_medidas_patch(fields: dict) -> dict:
    unidad = fields.get("unidad_medida", "in")
    for key in ("altura_total_in", "medida_cabeza_asiento", "medida_hombro_asiento", "medida_prof_asiento", "medida_rodilla_talon", "medida_ancho_cadera"):
        if key in fields:
            fields[key] = _to_inches(fields[key], unidad)
    return fields


@router.get("/solicitudes/{id}/foto")
def obtener_foto_solicitud(
    id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin"))],
) -> dict:
    if usuario.rol not in {"capturista", "tecnico", "admin"}:
        raise HTTPException(status_code=403, detail="No tiene permisos para esta acción")

    row = _load_solicitud_for_foto(db, id)
    if row is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    assert_resource_owner(row["usuario_id"], usuario)

    foto_path = extract_foto_path(row.get("foto_path")) or extract_foto_path(row.get("foto_url"))
    if foto_path is None:
        raise HTTPException(status_code=404, detail="Foto no disponible")

    derived_url = _derive_legacy_foto_url(foto_path)
    if extract_foto_path(row.get("foto_path")) is None:
        _try_backfill_foto_path(
            db,
            solicitud_id=id,
            foto_path=foto_path,
            foto_url=derived_url,
        )

    signed_raw = _storage().create_signed_url(foto_path, _SIGNED_URL_TTL_SECONDS)
    signed_url = _signed_url_from_response(signed_raw)
    if signed_url is None:
        raise HTTPException(status_code=500, detail="No se pudo generar URL firmada")

    return {
        "foto_path": foto_path,
        "url": signed_url,
        "expires_in": _SIGNED_URL_TTL_SECONDS,
    }
