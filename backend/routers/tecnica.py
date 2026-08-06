import io
import json
import os
import uuid
from decimal import Decimal
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone, date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator, model_validator, ValidationInfo
from supabase import create_client

from database import get_db, _DBAdapter
from audit import registrar_evento
from routers.auth import CurrentUser, _assert_case_pair, assert_resource_owner, require_roles
from validators import (
    validate_padecimiento,
    validate_medida_tecnica,
    validate_entidad_solicitante,
    validate_justificacion,
    validate_entorno,
    validate_control_tronco,
    validate_control_cabeza,
    validate_control_de_piernas,
    validate_unidad_medida,
    validate_unidad_peso,
    validate_prioridad,
    validate_status,
    validate_diagnostico,
    convert_medida_to_in,
    convert_peso_to_lb,
    normalize_medidas_to_canonical,
    MEDIDA_TECNICA_COLUMNS,
)
from utils.text import normalize_text

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_BUCKET = "fotos-tecnica"
_SIGNED_URL_TTL_SECONDS = 60
_STORAGE_URL_PREFIX = f"storage://{_BUCKET}/"

_DOCUMENT_BUCKET = "documentos-estudio"
_DOCUMENT_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_DOCUMENT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: object) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)


def _resolve_storage_url(raw_url: Optional[str], bucket: str) -> Optional[str]:
    """Resolve a storage:// reference or bare path into a browser-accessible URL."""
    if not raw_url:
        return None

    # Already a public URL — pass through
    if raw_url.startswith(("http://", "https://")):
        return raw_url

    # Extract path from storage://bucket/path
    path: Optional[str] = None
    prefix = f"storage://{bucket}/"
    if raw_url.startswith(prefix):
        path = raw_url[len(prefix):].strip("/")
    else:
        # Generic storage:// with bucket marker
        marker = f"/{bucket}/"
        if marker in raw_url:
            path = raw_url.split(marker, 1)[1].strip("/")
        else:
            # Bare path (legacy fallback)
            path = raw_url.strip("/")

    if not path:
        return None

    try:
        from supabase import create_client
        storage = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        ).storage.from_(bucket)
        signed_raw = storage.create_signed_url(path, 300)
        signed = _signed_url_from_response(signed_raw)
        if signed:
            return signed
    except Exception:
        pass

    # Fallback to public URL
    try:
        from supabase import create_client
        storage = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        ).storage.from_(bucket)
        return storage.get_public_url(path)
    except Exception:
        pass

    return None


def _build_list_where_clause(
    *,
    q: Optional[str],
    sede: Optional[str],
    pais_id: Optional[int] = None,
    region_id: Optional[int] = None,
    ciudad: Optional[str] = None,
    peso_kg_min: Optional[float] = None,
    peso_kg_max: Optional[float] = None,
    altura_in_min: Optional[float] = None,
    altura_in_max: Optional[float] = None,
    tiene_foto: Optional[bool] = None,
) -> tuple[str, list]:
    clauses: list[str] = ["1=1"]
    params: list = []

    # ── Range validation ──────────────────────────────────────────────────
    if peso_kg_min is not None and peso_kg_max is not None and peso_kg_min > peso_kg_max:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "invalid_filter",
                "message": "peso_kg_min no puede ser mayor que peso_kg_max",
            },
        )
    if altura_in_min is not None and altura_in_max is not None and altura_in_min > altura_in_max:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "invalid_filter",
                "message": "altura_in_min no puede ser mayor que altura_in_max",
            },
        )

    # ── Free-text search (expanded) ───────────────────────────────────────
    if q and q.strip():
        term = f"%{q.strip()}%"
        clauses.append(
            "(b.nombre ILIKE %s OR b.curp_benef ILIKE %s OR "
            "b.ciudad ILIKE %s OR "
            "r.nombre ILIKE %s OR "
            "p.nombre ILIKE %s)"
        )
        params.extend([term, term, term, term, term])

    # ── Sede ──────────────────────────────────────────────────────────────
    if sede and sede.strip():
        clauses.append("COALESCE(e.sede, '') = %s")
        params.append(sede.strip())

    # ── Pais (via region) ─────────────────────────────────────────────────
    if pais_id is not None:
        clauses.append("r.pais_id = %s")
        params.append(pais_id)

    # ── Region ────────────────────────────────────────────────────────────
    if region_id is not None:
        clauses.append("b.region_id = %s")
        params.append(region_id)

    # ── Ciudad ────────────────────────────────────────────────────────────
    if ciudad and ciudad.strip():
        term = f"%{ciudad.strip()}%"
        clauses.append("b.ciudad ILIKE %s")
        params.append(term)

    # ── Peso range ────────────────────────────────────────────────────────
    if peso_kg_min is not None:
        clauses.append("st.peso_kg >= %s")
        params.append(peso_kg_min)
    if peso_kg_max is not None:
        clauses.append("st.peso_kg <= %s")
        params.append(peso_kg_max)

    # ── Altura range ─────────────────────────────────────────────────────
    if altura_in_min is not None:
        clauses.append("st.altura_total_in >= %s")
        params.append(altura_in_min)
    if altura_in_max is not None:
        clauses.append("st.altura_total_in <= %s")
        params.append(altura_in_max)

    # ── Tiene foto ───────────────────────────────────────────────────────
    if tiene_foto is True:
        clauses.append("st.foto_url IS NOT NULL")
    elif tiene_foto is False:
        clauses.append("st.foto_url IS NULL")

    return " AND ".join(clauses), params


def _build_snapshot(db: _DBAdapter, beneficiario_id: int) -> dict:
    beneficiario = _row_to_dict(
        db.execute(
            """
            SELECT b.*,
                   COALESCE(p.nombre, '') AS pais_nombre,
                   COALESCE(r.nombre, '') AS region_nombre
            FROM beneficiarios b
            LEFT JOIN regiones r ON r.id = b.region_id
            LEFT JOIN paises p ON p.id = r.pais_id
            WHERE b.id = %s
            """,
            (beneficiario_id,),
        ).fetchone()
    )
    if beneficiario is None:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")

    tutores = db.execute(
        "SELECT * FROM tutores WHERE beneficiario_id = %s ORDER BY numero_tutor", (beneficiario_id,)
    ).fetchall()
    estudio = _row_to_dict(
        db.execute(
            """
            SELECT * FROM estudios_socioeconomicos
            WHERE beneficiario_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (beneficiario_id,),
        ).fetchone()
    )
    if estudio:
        if estudio.get("credencial_url"):
            estudio["credencial_url_resolved"] = _resolve_storage_url(
                estudio["credencial_url"], "documentos-estudio"
            )
        if estudio.get("comprobante_domicilio_url"):
            estudio["comprobante_domicilio_url_resolved"] = _resolve_storage_url(
                estudio["comprobante_domicilio_url"], "documentos-estudio"
            )
        if estudio.get("estudio_clinico_url"):
            estudio["estudio_clinico_url_resolved"] = _resolve_storage_url(
                estudio["estudio_clinico_url"], "documentos-estudio"
            )

    solicitud = _row_to_dict(
        db.execute(
            """
            SELECT * FROM solicitudes_tecnicas
            WHERE beneficiario_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (beneficiario_id,),
        ).fetchone()
    )
    if solicitud and solicitud.get("foto_url"):
        solicitud["foto_url_resolved"] = _resolve_storage_url(
            solicitud["foto_url"], "fotos-tecnica"
        )

    return {
        "beneficiario": beneficiario,
        "tutores": tutores,
        "estudio": estudio,
        "solicitud": solicitud,
    }


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


def _storage(bucket: str = _BUCKET):
    from supabase import create_client
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    ).storage.from_(bucket)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SolicitudCreateRequest(BaseModel):
    beneficiario_id: int
    entorno: str
    diagnostico: Optional[str] = None
    control_tronco: str
    control_cabeza: str
    control_de_piernas: str
    padecimiento: Optional[str] = None
    soporte_oxigeno: bool = False
    unidad_medida: str = "in"
    altura_total_in: Optional[Decimal] = None
    peso_kg: Optional[Decimal] = None
    unidad_peso_captura: str = "kg"
    medida_cabeza_asiento: Optional[Decimal] = None
    medida_hombro_asiento: Optional[Decimal] = None
    medida_prof_asiento: Optional[Decimal] = None
    medida_rodilla_talon: Optional[Decimal] = None
    medida_ancho_cadera: Optional[Decimal] = None
    foto_path: Optional[str] = None
    foto_url: Optional[str] = None
    equipo_solicitado: Optional[str] = None
    estudio_clinico_path: Optional[str] = None
    estudio_clinico_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
    status: str = "borrador"

    @field_validator("entorno")
    @classmethod
    def _entorno_valido(cls, v: str) -> str:
        return validate_entorno(v)

    @field_validator("diagnostico", mode="before")
    @classmethod
    def validate_diagnostico_field(cls, v) -> Optional[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_diagnostico(normalize_text(str(v)) or "")

    @field_validator("control_tronco")
    @classmethod
    def _control_tronco_valido(cls, v: str) -> str:
        return validate_control_tronco(v)

    @field_validator("control_cabeza")
    @classmethod
    def _control_cabeza_valido(cls, v: str) -> str:
        return validate_control_cabeza(v)

    @field_validator("control_de_piernas")
    @classmethod
    def _control_de_piernas_valido(cls, v: str) -> str:
        return validate_control_de_piernas(v)

    @field_validator("padecimiento", mode="before")
    @classmethod
    def validate_obs_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_padecimiento(normalize_text(str(v)) or "")

    @field_validator("unidad_medida")
    @classmethod
    def _unidad_valida(cls, v: str) -> str:
        return validate_unidad_medida(v)

    @field_validator("unidad_peso_captura")
    @classmethod
    def _unidad_peso_valida(cls, v: str) -> str:
        return validate_unidad_peso(v)

    @field_validator("altura_total_in", "peso_kg", "medida_cabeza_asiento",
                     "medida_hombro_asiento", "medida_prof_asiento",
                     "medida_rodilla_talon", "medida_ancho_cadera", mode="before")
    @classmethod
    def validate_medida_field(cls, v, info: ValidationInfo) -> Optional[Decimal]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_medida_tecnica(str(v), info.field_name)

    @field_validator("entidad_solicitante", mode="before")
    @classmethod
    def validate_entidad_solicitante_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_entidad_solicitante(normalize_text(str(v)) or "")

    @field_validator("prioridad")
    @classmethod
    def _prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_prioridad(v)

    @field_validator("justificacion", mode="before")
    @classmethod
    def validate_justificacion_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_justificacion(normalize_text(str(v)) or "")

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: str) -> str:
        return validate_status(v)

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
    diagnostico: Optional[str] = None
    control_tronco: Optional[str] = None
    control_cabeza: Optional[str] = None
    control_de_piernas: Optional[str] = None
    padecimiento: Optional[str] = None
    soporte_oxigeno: Optional[bool] = None
    unidad_medida: Optional[str] = None
    altura_total_in: Optional[Decimal] = None
    peso_kg: Optional[Decimal] = None
    unidad_peso_captura: Optional[str] = None
    medida_cabeza_asiento: Optional[Decimal] = None
    medida_hombro_asiento: Optional[Decimal] = None
    medida_prof_asiento: Optional[Decimal] = None
    medida_rodilla_talon: Optional[Decimal] = None
    medida_ancho_cadera: Optional[Decimal] = None
    foto_path: Optional[str] = None
    foto_url: Optional[str] = None
    equipo_solicitado: Optional[str] = None
    estudio_clinico_path: Optional[str] = None
    estudio_clinico_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
    status: Optional[str] = None

    @field_validator("entorno")
    @classmethod
    def _entorno_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_entorno(v)

    @field_validator("diagnostico", mode="before")
    @classmethod
    def validate_diagnostico_field(cls, v) -> Optional[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_diagnostico(normalize_text(str(v)) or "")

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

    @field_validator("control_de_piernas")
    @classmethod
    def _control_de_piernas_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_control_de_piernas(v)

    @field_validator("padecimiento", mode="before")
    @classmethod
    def validate_obs_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_padecimiento(normalize_text(str(v)) or "")

    @field_validator("unidad_medida")
    @classmethod
    def _unidad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_unidad_medida(v)

    @field_validator("unidad_peso_captura")
    @classmethod
    def _unidad_peso_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_unidad_peso(v)

    @field_validator("altura_total_in", "peso_kg", "medida_cabeza_asiento",
                     "medida_hombro_asiento", "medida_prof_asiento",
                     "medida_rodilla_talon", "medida_ancho_cadera", mode="before")
    @classmethod
    def validate_medida_field(cls, v, info: ValidationInfo) -> Optional[Decimal]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_medida_tecnica(str(v), info.field_name)

    @field_validator("entidad_solicitante", mode="before")
    @classmethod
    def validate_entidad_solicitante_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_entidad_solicitante(normalize_text(str(v)) or "")

    @field_validator("prioridad")
    @classmethod
    def _prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_prioridad(v)

    @field_validator("justificacion", mode="before")
    @classmethod
    def validate_justificacion_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_justificacion(normalize_text(str(v)) or "")

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_status(v)

    # NOTA (Issue #129): NO se valida aquí la completitud de medidas al cerrar
    # (status="completo"). Este es un modelo de actualización PARCIAL y Pydantic
    # no tiene acceso a la BD, por lo que no puede conocer las medidas ya
    # persistidas en el borrador. La verificación de completitud contra el estado
    # FUSIONADO (cuerpo + BD) se hace en el endpoint `actualizar_solicitud`, que
    # sí tiene acceso a la BD (mismo enfoque que `finalizar._validate_all_complete`).


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


@router.get("/tecnica/beneficiarios")
def listar_beneficiarios_tecnica(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("tecnico", "admin"))],
    q: Optional[str] = None,
    sede: Optional[str] = None,
    pais_id: Optional[int] = None,
    region_id: Optional[int] = None,
    ciudad: Optional[str] = None,
    peso_kg_min: Optional[float] = None,
    peso_kg_max: Optional[float] = None,
    altura_in_min: Optional[float] = None,
    altura_in_max: Optional[float] = None,
    tiene_foto: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    if page < 1:
        raise HTTPException(
            status_code=422,
            detail={"type": "invalid_filter", "message": "page debe ser >= 1"},
        )
    if per_page < 1:
        raise HTTPException(
            status_code=422,
            detail={"type": "invalid_filter", "message": "per_page debe ser >= 1"},
        )

    where_clause, params = _build_list_where_clause(
        q=q,
        sede=sede,
        pais_id=pais_id,
        region_id=region_id,
        ciudad=ciudad,
        peso_kg_min=peso_kg_min,
        peso_kg_max=peso_kg_max,
        altura_in_min=altura_in_min,
        altura_in_max=altura_in_max,
        tiene_foto=tiene_foto,
    )

    offset = (page - 1) * per_page

    rows = db.execute(
        f"""
        SELECT
            b.id AS beneficiario_id,
            b.nombre,
            b.curp_benef,
            b.telefonos,
            b.ciudad,
            COALESCE(p.nombre, '') AS pais_nombre,
            COALESCE(r.nombre, '') AS region_nombre,
            COALESCE(e.sede, '') AS sede,
            st.peso_kg,
            st.altura_total_in,
            st.unidad_captura,
            st.foto_url,
            st.status AS solicitud_status,
            COUNT(*) OVER() AS total_count
        FROM beneficiarios b
        LEFT JOIN estudios_socioeconomicos e ON e.beneficiario_id = b.id
        LEFT JOIN solicitudes_tecnicas st ON st.beneficiario_id = b.id
        LEFT JOIN regiones r ON r.id = b.region_id
        LEFT JOIN paises p ON p.id = r.pais_id
        WHERE {where_clause}
        ORDER BY b.nombre ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (per_page, offset),
    ).fetchall()

    total = rows[0]["total_count"] if rows else 0

    return {
        "items": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def _calcular_edad(fecha_nacimiento_str: Optional[str]) -> Optional[int]:
    """Calcular edad en años a partir de fecha_nacimiento (texto)."""
    if not fecha_nacimiento_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            born = datetime.strptime(fecha_nacimiento_str.strip(), fmt).date()
            today = date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except ValueError:
            continue
    return None


@router.get("/tecnica/beneficiarios/export")
def exportar_beneficiarios_tecnica(
    request: Request,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("tecnico", "admin"))],
    q: Optional[str] = None,
    sede: Optional[str] = None,
    pais_id: Optional[int] = None,
    region_id: Optional[int] = None,
    ciudad: Optional[str] = None,
    peso_kg_min: Optional[float] = None,
    peso_kg_max: Optional[float] = None,
    altura_in_min: Optional[float] = None,
    altura_in_max: Optional[float] = None,
    tiene_foto: Optional[bool] = None,
    ids: Optional[str] = None,
) -> StreamingResponse:
    where_clause, params = _build_list_where_clause(
        q=q,
        sede=sede,
        pais_id=pais_id,
        region_id=region_id,
        ciudad=ciudad,
        peso_kg_min=peso_kg_min,
        peso_kg_max=peso_kg_max,
        altura_in_min=altura_in_min,
        altura_in_max=altura_in_max,
        tiene_foto=tiene_foto,
    )

    ids_list: list[int] = []
    if ids:
        try:
            ids_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={"type": "invalid_filter", "message": "ids debe ser una lista de enteros separados por coma"},
            )
    if ids_list:
        placeholders = ",".join(["%s"] * len(ids_list))
        where_clause += f" AND b.id IN ({placeholders})"
        params.extend(ids_list)

    rows = db.execute(
        f"""
        SELECT
            b.id AS beneficiario_id,
            b.curp_benef,
            b.nombre,
            b.email,
            b.calle,
            b.num_ext,
            b.colonia,
            b.ciudad,
            b.estado_nombre,
            b.telefonos,
            b.diagnostico,
            b.fecha_nacimiento,
            st.peso_kg,
            st.altura_total_in,
            st.unidad_captura,
            st.padecimiento,
            st.justificacion,
            st.entidad_solicitante,
            t.nombre AS tutor_nombre
        FROM beneficiarios b
        LEFT JOIN estudios_socioeconomicos e ON e.beneficiario_id = b.id
        LEFT JOIN solicitudes_tecnicas st ON st.beneficiario_id = b.id
        LEFT JOIN regiones r ON r.id = b.region_id
        LEFT JOIN paises p ON p.id = r.pais_id
        LEFT JOIN LATERAL (
            SELECT nombre FROM tutores WHERE beneficiario_id = b.id ORDER BY numero_tutor LIMIT 1
        ) t ON true
        WHERE {where_clause}
        ORDER BY b.nombre ASC
        """,
        tuple(params),
    ).fetchall()

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.table import Table, TableStyleInfo
    wb = Workbook()
    ws = wb.active
    ws.title = "MASTER"

    headers = [
        "# EXPEDIENTE",
        "Nombre de Niño(a) Adolescente",
        "Correo electrónico ",
        "Dirección (calle, numero)",
        "Colonia o comunidad",
        "Municipio (ciudad) y Estado",
        "Número de teléfono Fijo",
        "No. de teléfono adicional",
        "Padecimiento",
        "Fecha de nacimiento",
        "EDAD",
        "PESO (lb)",
        "ESTATURA (in)",
        "Nombre de Padre o tutor",
        "Club o A sociación",
        "QUIEN CANALIZA",
        "OBSERVACIONES ",
    ]

    # Fila 1 vacía (plantilla original tiene fila 1 vacía)
    ws.append([])
    # Fila 2: headers
    ws.append(headers)

    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in ws[2]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row in rows:
        direccion = (row["calle"] or "") + (f' {row["num_ext"]}' if row.get("num_ext") else "")
        municipio_estado = (row["ciudad"] or "") + (f', {row["estado_nombre"]}' if row.get("estado_nombre") else "")

        altura_in = row.get("altura_total_in")

        edad = _calcular_edad(row.get("fecha_nacimiento"))

        ws.append([
            row.get("curp_benef") or row.get("beneficiario_id"),
            row.get("nombre") or "",
            row.get("email") or "Sin correo",
            direccion,
            row.get("colonia") or "",
            municipio_estado,
            row.get("telefonos") or "",
            "",  # teléfono adicional — no hay campo separado
            row.get("diagnostico") or "",
            row.get("fecha_nacimiento") or "",
            edad,
            row.get("peso_kg"),
            altura_in,
            row.get("tutor_nombre") or "",
            row.get("entidad_solicitante") or "",  # Club o Asociación — mapeamos a entidad solicitante
            "",  # QUIEN CANALIZA — no hay campo
            row.get("padecimiento") or "",
        ])

    ws.freeze_panes = "A3"

    column_widths = {
        "A": 18,
        "B": 34,
        "C": 24,
        "D": 28,
        "E": 24,
        "F": 28,
        "G": 20,
        "H": 20,
        "I": 24,
        "J": 18,
        "K": 10,
        "L": 12,
        "M": 14,
        "N": 28,
        "O": 24,
        "P": 22,
        "Q": 34,
    }
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    if ws.max_row >= 2:
        table = Table(displayName="BeneficiariosTecnica", ref=f"A2:Q{ws.max_row}")
        style = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        table.tableStyleInfo = style
        ws.add_table(table)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    registrar_evento(
        db,
        actor=usuario,
        accion="export.generate",
        recurso_tipo="tecnica_beneficiarios",
        recurso_id="bulk",
        metadata={"row_count": len(rows), "ids_count": len(ids_list), "filters_applied": bool(params)},
        request=request,
    )

    filename = f"BASE_DE_DATOS_EXPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tecnica/beneficiarios/{beneficiario_id}")
def obtener_detalle_tecnico(
    beneficiario_id: int,
    request: Request,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("tecnico", "admin"))],
) -> dict:
    snapshot = _build_snapshot(db, beneficiario_id)
    snapshot["permisos"] = {
        "readonly_base": True,
    }
    registrar_evento(
        db,
        actor=usuario,
        accion="beneficiario.detail.view",
        recurso_tipo="beneficiario",
        recurso_id=beneficiario_id,
        metadata={"surface": "tecnica"},
        request=request,
    )
    return snapshot


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload-foto")
async def upload_foto(
    foto: UploadFile = File(...),
    _usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "organizacion"))] = None,
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

    canonical_url = _derive_legacy_foto_url(filename)
    return {
        "foto_path": filename,
        "foto_url": canonical_url,
        # Browser-renderable URL for immediate preview — the canonical
        # storage:// reference above is what gets persisted in the DB.
        "foto_url_resolved": _resolve_storage_url(canonical_url, _BUCKET),
    }


@router.post("/upload-estudio-clinico")
async def upload_estudio_clinico(
    archivo: UploadFile = File(...),
    _usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "organizacion"))] = None,
) -> dict:
    """Upload a clinical study document (JPG, PNG, or PDF) to documentos-estudio bucket."""
    if archivo.content_type not in _DOCUMENT_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    _, ext = os.path.splitext(archivo.filename or "")
    if ext.lower() not in _DOCUMENT_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    data = await archivo.read()
    if len(data) > _MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="El archivo excede 10MB")

    filename = f"estudio_clinico/{uuid.uuid4()}{ext.lower()}"

    try:
        _storage(_DOCUMENT_BUCKET).upload(
            path=filename,
            file=data,
            file_options={"content-type": archivo.content_type},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error al subir el estudio clínico") from exc

    canonical_url = f"storage://{_DOCUMENT_BUCKET}/{filename}"
    return {
        "estudio_clinico_path": filename,
        "estudio_clinico_url": canonical_url,
        "estudio_clinico_url_resolved": _resolve_storage_url(canonical_url, _DOCUMENT_BUCKET),
    }


@router.post("/solicitudes", status_code=201, response_model=SolicitudCreateResponse)
def crear_solicitud(
    body: SolicitudCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "organizacion"))],
) -> SolicitudCreateResponse:
    _assert_case_pair(
        beneficiario_id=body.beneficiario_id,
        user=usuario,
        db=db,
    )
    # Normalize units only on final submission (status=completo).
    # For borradores, store values exactly as sent so open/save cycles
    # are idempotent and do not compound conversion errors.
    if body.status != "borrador":
        body = _normalize_medidas(body)
    existing = db.execute(
        """
        SELECT id FROM solicitudes_tecnicas
        WHERE beneficiario_id = %s AND usuario_id = %s
        LIMIT 1
        """,
        (body.beneficiario_id, usuario.usuario_id),
    ).fetchone()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una solicitud técnica para este beneficiario y usuario",
        )

    resolved_foto_path, resolved_foto_url = _resolve_foto_refs(
        foto_path=body.foto_path,
        foto_url=body.foto_url,
    )

    try:
        solicitud_id = db.execute(
            """
            INSERT INTO solicitudes_tecnicas
                (beneficiario_id, usuario_id, entorno, control_tronco, control_cabeza, control_de_piernas,
                 padecimiento,
                 soporte_oxigeno, altura_total_in, peso_kg,
                 medida_cabeza_asiento, medida_hombro_asiento, medida_prof_asiento,
                 medida_rodilla_talon, medida_ancho_cadera, unidad_captura, unidad_peso_captura, foto_url,
                 equipo_solicitado, estudio_clinico_path, estudio_clinico_url,
                 entidad_solicitante, prioridad, justificacion, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.beneficiario_id,
                usuario.usuario_id,
                body.entorno,
                body.control_tronco,
                body.control_cabeza,
                body.control_de_piernas,
                body.padecimiento,
                body.soporte_oxigeno,
                body.altura_total_in,
                body.peso_kg,
                body.medida_cabeza_asiento,
                body.medida_hombro_asiento,
                body.medida_prof_asiento,
                body.medida_rodilla_talon,
                body.medida_ancho_cadera,
                body.unidad_medida,
                body.unidad_peso_captura,
                resolved_foto_url,
                body.equipo_solicitado,
                body.estudio_clinico_path,
                body.estudio_clinico_url,
                body.entidad_solicitante,
                body.prioridad,
                body.justificacion,
                body.status,
            ),
        ).fetchone()["id"]
    except Exception as exc:
        raise _classify_db_error(exc) from exc

    if body.diagnostico is not None:
        db.execute(
            "UPDATE beneficiarios SET diagnostico = %s WHERE id = %s",
            (body.diagnostico, body.beneficiario_id),
        )

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
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin", "organizacion"))],
) -> dict:
    row = db.execute(
        "SELECT * FROM solicitudes_tecnicas WHERE id = %s", (id,)
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    assert_resource_owner(row["usuario_id"], usuario, db=db)

    out = dict(row)
    beneficiario = db.execute(
        "SELECT diagnostico FROM beneficiarios WHERE id = %s",
        (row["beneficiario_id"],),
    ).fetchone()
    out["diagnostico"] = beneficiario["diagnostico"] if beneficiario else None
    # Resolve storage URL so the frontend preview can render it without
    # needing a separate fetch — raw storage:// URIs cannot be used as <img src>.
    if out.get("foto_url"):
        out["foto_url_resolved"] = _resolve_storage_url(out["foto_url"], _BUCKET)
    if out.get("estudio_clinico_url"):
        out["estudio_clinico_url_resolved"] = _resolve_storage_url(out["estudio_clinico_url"], _DOCUMENT_BUCKET)
    else:
        estudio = db.execute(
            """
            SELECT estudio_clinico_path, estudio_clinico_url
            FROM estudios_socioeconomicos
            WHERE beneficiario_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (row["beneficiario_id"],),
        ).fetchone()
        if estudio and estudio.get("estudio_clinico_url"):
            out["estudio_clinico_path"] = estudio.get("estudio_clinico_path")
            out["estudio_clinico_url"] = estudio["estudio_clinico_url"]
            out["estudio_clinico_url_resolved"] = _resolve_storage_url(estudio["estudio_clinico_url"], _DOCUMENT_BUCKET)
    return out


@router.patch("/solicitudes/{id}", response_model=SolicitudUpdateResponse)
def actualizar_solicitud(
    id: int,
    body: SolicitudUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "organizacion"))],
) -> SolicitudUpdateResponse:
    existing = db.execute(
        """SELECT id, usuario_id, beneficiario_id, status,
                  unidad_captura, unidad_peso_captura,
                  altura_total_in, medida_cabeza_asiento, medida_hombro_asiento,
                  medida_prof_asiento, medida_rodilla_talon, medida_ancho_cadera,
                  peso_kg
           FROM solicitudes_tecnicas WHERE id = %s""", (id,)
    ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    _assert_case_pair(solicitud_id=id, user=usuario, db=db)

    fields = body.model_dump(exclude_none=True)

    # Issue #129: al cerrar (status="completo") las 7 medidas se validan aquí,
    # contra el estado FUSIONADO (lo enviado en el cuerpo + lo ya persistido en
    # `solicitudes_tecnicas` desde el borrador). Se hace en el endpoint —no en el
    # modelo Pydantic— porque aquí sí hay acceso a la BD. La autorización
    # (`_assert_case_pair`) ya se evaluó arriba, de modo que un ajeno recibe
    # 403 antes de llegar a esta validación. Mismo enfoque que
    # `finalizar._validate_all_complete`.
    if fields.get("status") == "completo":
        _MEDIDA_COLS = (
            "altura_total_in", "peso_kg",
            "medida_cabeza_asiento", "medida_hombro_asiento",
            "medida_prof_asiento", "medida_rodilla_talon",
            "medida_ancho_cadera",
        )
        faltantes = [
            col for col in _MEDIDA_COLS
            if fields.get(col) is None and existing[col] is None
        ]
        if faltantes:
            raise HTTPException(
                status_code=422,
                detail=f"{', '.join(faltantes)} es obligatorio cuando status es completo",
            )

    # Diagnostico lives on beneficiarios, not solicitudes_tecnicas
    diagnostico = fields.pop("diagnostico", None)
    if diagnostico is not None:
        db.execute(
            "UPDATE beneficiarios SET diagnostico = %s WHERE id = %s",
            (diagnostico, existing["beneficiario_id"]),
        )
    # Normalize units only when finalizing (status becomes completo).
    # For borradores, store measurement values exactly as sent so that
    # repeated save/reopen cycles are idempotent.
    if fields.get("status") != "borrador" and (
        fields.get("unidad_medida") in ("cm", "in") or "unidad_peso_captura" in fields
    ):
        fields = _normalize_medidas_patch(fields)
    elif (
        fields.get("status") == "completo"
        and "unidad_medida" not in fields
        and existing["status"] != "completo"
    ):
        # Finalizing (first borrador -> completo transition) without a
        # body-provided measurement unit: use the stored capture unit to
        # convert measurement values to canonical inches/lb so they are not
        # silently promoted with the wrong unit. Guarded by
        # existing["status"] != "completo" because unidad_captura/
        # unidad_peso_captura are a permanent audit trail (never updated to
        # reflect "already converted") — without this guard, a repeated
        # PATCH with status="completo" on an already-completo record would
        # re-convert already-canonical values a second time.
        stored_unidad = existing["unidad_captura"] or "in"
        stored_unidad_peso = existing["unidad_peso_captura"] or "lb"
        effective = {
            col: (fields[col] if col in fields else existing[col])
            for col in MEDIDA_TECNICA_COLUMNS
        }
        effective["peso_kg"] = fields["peso_kg"] if "peso_kg" in fields else existing["peso_kg"]
        fields.update(normalize_medidas_to_canonical(
            effective,
            unidad_medida=stored_unidad,
            unidad_peso_captura=stored_unidad_peso,
        ))
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
    return convert_medida_to_in(v, unidad)


def _to_kg(v: Optional[Decimal], unidad: str) -> Optional[Decimal]:
    """Convert a weight value to pounds (canonical storage unit)."""
    return convert_peso_to_lb(v, unidad)


def _normalize_medidas(body: SolicitudCreateRequest) -> SolicitudCreateRequest:
    data = body.model_dump()
    unidad = data.get("unidad_medida", "in")
    unidad_peso = data.get("unidad_peso_captura", "kg")
    for key in ("altura_total_in", "medida_cabeza_asiento", "medida_hombro_asiento", "medida_prof_asiento", "medida_rodilla_talon", "medida_ancho_cadera"):
        data[key] = _to_inches(data.get(key), unidad)
    data["peso_kg"] = _to_kg(data.get("peso_kg"), unidad_peso)
    return SolicitudCreateRequest(**data)


def _normalize_medidas_patch(fields: dict) -> dict:
    unidad = fields.get("unidad_medida", "in")
    unidad_peso = fields.get("unidad_peso_captura", "kg")
    for key in ("altura_total_in", "medida_cabeza_asiento", "medida_hombro_asiento", "medida_prof_asiento", "medida_rodilla_talon", "medida_ancho_cadera"):
        if key in fields:
            fields[key] = _to_inches(fields[key], unidad)
    if "peso_kg" in fields:
        fields["peso_kg"] = _to_kg(fields["peso_kg"], unidad_peso)
    return fields


@router.get("/solicitudes/{id}/foto")
def obtener_foto_solicitud(
    id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin", "organizacion"))],
    request: Request = None,
) -> dict:
    if usuario.rol not in {"capturista", "tecnico", "admin", "organizacion"}:
        raise HTTPException(status_code=403, detail="No tiene permisos para esta acción")

    row = _load_solicitud_for_foto(db, id)
    if row is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    assert_resource_owner(row["usuario_id"], usuario, db=db)

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

    registrar_evento(
        db,
        actor=usuario,
        accion="signed_url.generate",
        recurso_tipo="solicitud_foto",
        recurso_id=id,
        metadata={"bucket": _BUCKET, "expires_in": _SIGNED_URL_TTL_SECONDS},
        request=request,
    )

    return {
        "foto_path": foto_path,
        "url": signed_url,
        "expires_in": _SIGNED_URL_TTL_SECONDS,
    }
