import io
import os
import uuid
from decimal import Decimal
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone, date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
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
    validate_control_de_piernas,
    validate_unidad_medida,
    validate_unidad_peso,
    validate_prioridad,
    validate_status,
    validate_diagnostico,
)
from utils.text import normalize_text

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_BUCKET = "fotos-tecnica"
_SIGNED_URL_TTL_SECONDS = 60
_STORAGE_URL_PREFIX = f"storage://{_BUCKET}/"
_PROCESS_STATES = {"sin_iniciar", "en_proceso", "finalizado", "revision_pendiente"}
_PROCESS_ACTIONS = {"iniciar", "continuar", "finalizar", "solicitar_revision"}


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
    estado: Optional[str],
    revision_pendiente: Optional[bool],
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
            "(b.nombre ILIKE %s OR b.folio ILIKE %s OR "
            "b.ciudad ILIKE %s OR "
            "r.nombre ILIKE %s OR "
            "p.nombre ILIKE %s)"
        )
        params.extend([term, term, term, term, term])

    # ── Sede ──────────────────────────────────────────────────────────────
    if sede and sede.strip():
        clauses.append("COALESCE(e.sede, '') = %s")
        params.append(sede.strip())

    # ── Estado ────────────────────────────────────────────────────────────
    if estado and estado.strip():
        if estado not in _PROCESS_STATES:
            raise HTTPException(
                status_code=422,
                detail={"type": "invalid_filter", "message": "estado no válido"},
            )
        clauses.append("COALESCE(pt.estado, 'sin_iniciar') = %s")
        params.append(estado)

    # ── Revision pendiente ───────────────────────────────────────────────
    if revision_pendiente is not None:
        clauses.append("COALESCE(pt.revision_pendiente, FALSE) = %s")
        params.append(revision_pendiente)

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


def _upsert_participant(
    db: _DBAdapter,
    *,
    proceso_id: int,
    usuario_id: int,
    accion: str,
) -> None:
    db.execute(
        """
        INSERT INTO procesos_tecnicos_participantes (proceso_tecnico_id, usuario_id, accion)
        VALUES (%s, %s, %s)
        """,
        (proceso_id, usuario_id, accion),
    )


def _load_proceso(db: _DBAdapter, proceso_id: int) -> dict:
    row = _row_to_dict(
        db.execute("SELECT * FROM procesos_tecnicos WHERE id = %s", (proceso_id,)).fetchone()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Proceso técnico no encontrado")
    return row


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
    proceso = _row_to_dict(
        db.execute(
            "SELECT * FROM procesos_tecnicos WHERE beneficiario_id = %s",
            (beneficiario_id,),
        ).fetchone()
    )

    participantes: list[dict] = []
    if proceso is not None:
        participantes = db.execute(
            """
            SELECT p.usuario_id, u.nombre, p.accion, p.created_at
            FROM procesos_tecnicos_participantes p
            JOIN usuarios u ON u.id = p.usuario_id
            WHERE p.proceso_tecnico_id = %s
            ORDER BY p.created_at ASC
            """,
            (proceso["id"],),
        ).fetchall()

    return {
        "beneficiario": beneficiario,
        "tutores": tutores,
        "estudio": estudio,
        "solicitud": solicitud,
        "proceso_tecnico": proceso,
        "participantes": participantes,
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


def _storage():
    from supabase import create_client
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
    diagnostico: Optional[str] = None
    control_tronco: str
    control_cabeza: str
    control_de_piernas: str
    soporte_oxigeno: bool = False
    observaciones_posturales: Optional[str] = None
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

    @field_validator("observaciones_posturales", mode="before")
    @classmethod
    def validate_obs_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_observaciones_posturales(normalize_text(str(v)) or "")

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
    soporte_oxigeno: Optional[bool] = None
    observaciones_posturales: Optional[str] = None
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

    @field_validator("observaciones_posturales", mode="before")
    @classmethod
    def validate_obs_field(cls, v) -> Optional[str]:
        if v is None:
            return None
        return validate_observaciones_posturales(normalize_text(str(v)) or "")

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


def apply_tecnico_transition(current_state: str, action: str) -> str:
    if current_state not in _PROCESS_STATES:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "invalid_state",
                "message": "Estado operativo no reconocido",
            },
        )

    if action not in _PROCESS_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "invalid_action",
                "message": "Acción operativa no reconocida",
            },
        )

    transitions = {
        ("sin_iniciar", "iniciar"): "en_proceso",
        ("en_proceso", "continuar"): "en_proceso",
        ("en_proceso", "finalizar"): "finalizado",
        ("en_proceso", "solicitar_revision"): "revision_pendiente",
    }

    next_state = transitions.get((current_state, action))
    if next_state is None:
        raise HTTPException(
            status_code=409,
            detail={
                "type": "invalid_transition",
                "message": f"No se permite '{action}' desde estado '{current_state}'",
            },
        )
    return next_state


def ensure_single_process_per_beneficiario(existing_process: Optional[dict]) -> None:
    if existing_process is None:
        return
    raise HTTPException(
        status_code=409,
        detail={
            "type": "unique_violation",
            "message": "Ya existe un proceso técnico para este beneficiario",
        },
    )


def merge_participant_ids(current_participants: list[int], actor_user_id: int) -> list[int]:
    if actor_user_id in current_participants:
        return current_participants
    return [*current_participants, actor_user_id]


@router.get("/tecnica/beneficiarios")
def listar_beneficiarios_tecnica(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("tecnico", "admin"))],
    q: Optional[str] = None,
    sede: Optional[str] = None,
    estado: Optional[str] = None,
    revision_pendiente: Optional[bool] = None,
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
        estado=estado,
        revision_pendiente=revision_pendiente,
        pais_id=pais_id,
        region_id=region_id,
        ciudad=ciudad,
        peso_kg_min=peso_kg_min,
        peso_kg_max=peso_kg_max,
        altura_in_min=altura_in_min,
        altura_in_max=altura_in_max,
        tiene_foto=tiene_foto,
    )

    # Técnicos only work on finalized captures — never on a capturista's
    # in-progress draft. Admins keep full visibility through this endpoint
    # (and the dedicated admin-beneficiarios view) and can still filter by
    # process estado explicitly.
    if _usuario.rol == "tecnico":
        where_clause += " AND COALESCE(e.status, 'borrador') = 'completo'"

    offset = (page - 1) * per_page

    rows = db.execute(
        f"""
        SELECT
            b.id AS beneficiario_id,
            b.nombre,
            b.folio,
            b.telefonos,
            b.ciudad,
            COALESCE(p.nombre, '') AS pais_nombre,
            COALESCE(r.nombre, '') AS region_nombre,
            COALESCE(e.sede, '') AS sede,
            COALESCE(pt.estado, 'sin_iniciar') AS estado,
            COALESCE(pt.revision_pendiente, FALSE) AS revision_pendiente,
            pt.id AS proceso_id,
            st.peso_kg,
            st.altura_total_in,
            st.unidad_captura,
            st.foto_url,
            st.status AS solicitud_status,
            COUNT(*) OVER() AS total_count
        FROM beneficiarios b
        LEFT JOIN estudios_socioeconomicos e ON e.beneficiario_id = b.id
        LEFT JOIN procesos_tecnicos pt ON pt.beneficiario_id = b.id
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
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("tecnico", "admin"))],
    q: Optional[str] = None,
    sede: Optional[str] = None,
    estado: Optional[str] = None,
    revision_pendiente: Optional[bool] = None,
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
        estado=estado,
        revision_pendiente=revision_pendiente,
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
            b.folio,
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
            st.observaciones_posturales,
            st.justificacion,
            st.entidad_solicitante,
            t.nombre AS tutor_nombre
        FROM beneficiarios b
        LEFT JOIN estudios_socioeconomicos e ON e.beneficiario_id = b.id
        LEFT JOIN procesos_tecnicos pt ON pt.beneficiario_id = b.id
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
            row.get("folio") or row.get("beneficiario_id"),
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
            row.get("observaciones_posturales") or "",
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

    filename = f"BASE_DE_DATOS_EXPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tecnica/beneficiarios/{beneficiario_id}")
def obtener_detalle_tecnico(
    beneficiario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("tecnico", "admin"))],
) -> dict:
    snapshot = _build_snapshot(db, beneficiario_id)
    snapshot["permisos"] = {
        "readonly_base": True,
        "can_operate": usuario.rol == "tecnico",
    }
    return snapshot


@router.post("/tecnica/beneficiarios/{beneficiario_id}/iniciar", status_code=201)
def iniciar_proceso_tecnico(
    beneficiario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("tecnico"))],
) -> dict:
    existente = _row_to_dict(
        db.execute("SELECT * FROM procesos_tecnicos WHERE beneficiario_id = %s", (beneficiario_id,)).fetchone()
    )
    if existente is not None:
        ensure_single_process_per_beneficiario(existente)

    row = _row_to_dict(
        db.execute(
            """
            INSERT INTO procesos_tecnicos (
                beneficiario_id,
                estado,
                responsable_actual_usuario_id,
                tecnico_inicio_usuario_id,
                fecha_inicio,
                fecha_ultimo_movimiento,
                revision_pendiente,
                pdf_snapshot_json
            )
            VALUES (%s, %s, %s, %s, NOW(), NOW(), FALSE, %s)
            RETURNING *
            """,
            (
                beneficiario_id,
                "en_proceso",
                usuario.usuario_id,
                usuario.usuario_id,
                "{}",
            ),
        ).fetchone()
    )
    if row is None:
        raise HTTPException(status_code=500, detail="No se pudo iniciar el proceso técnico")

    _upsert_participant(db, proceso_id=row["id"], usuario_id=usuario.usuario_id, accion="inicio")
    return {"proceso": row, "event": "inicio"}


@router.post("/tecnica/procesos/{proceso_id}/continuar")
def continuar_proceso_tecnico(
    proceso_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("tecnico"))],
) -> dict:
    proceso = _load_proceso(db, proceso_id)
    next_state = apply_tecnico_transition(proceso["estado"], "continuar")
    db.execute(
        """
        UPDATE procesos_tecnicos
        SET estado = %s,
            responsable_actual_usuario_id = %s,
            fecha_ultimo_movimiento = NOW(),
            updated_at = NOW()
        WHERE id = %s
        """,
        (next_state, usuario.usuario_id, proceso_id),
    )
    _upsert_participant(db, proceso_id=proceso_id, usuario_id=usuario.usuario_id, accion="continuacion")
    return {"proceso_id": proceso_id, "estado": next_state, "event": "continuacion"}


@router.post("/tecnica/procesos/{proceso_id}/finalizar")
def finalizar_proceso_tecnico(
    proceso_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("tecnico"))],
) -> dict:
    proceso = _load_proceso(db, proceso_id)
    next_state = apply_tecnico_transition(proceso["estado"], "finalizar")
    db.execute(
        """
        UPDATE procesos_tecnicos
        SET estado = %s,
            responsable_actual_usuario_id = %s,
            revision_pendiente = FALSE,
            fecha_ultimo_movimiento = NOW(),
            updated_at = NOW()
        WHERE id = %s
        """,
        (next_state, usuario.usuario_id, proceso_id),
    )
    _upsert_participant(db, proceso_id=proceso_id, usuario_id=usuario.usuario_id, accion="finalizacion")
    return {"proceso_id": proceso_id, "estado": next_state, "event": "finalizacion"}


@router.post("/tecnica/procesos/{proceso_id}/solicitar-revision")
def solicitar_revision_tecnica(
    proceso_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("tecnico"))],
) -> dict:
    proceso = _load_proceso(db, proceso_id)
    next_state = apply_tecnico_transition(proceso["estado"], "solicitar_revision")
    db.execute(
        """
        UPDATE procesos_tecnicos
        SET estado = %s,
            responsable_actual_usuario_id = %s,
            revision_pendiente = TRUE,
            fecha_ultimo_movimiento = NOW(),
            updated_at = NOW()
        WHERE id = %s
        """,
        (next_state, usuario.usuario_id, proceso_id),
    )
    _upsert_participant(db, proceso_id=proceso_id, usuario_id=usuario.usuario_id, accion="revision")
    return {"proceso_id": proceso_id, "estado": next_state, "revision_pendiente": True}


@router.get("/tecnica/procesos/{proceso_id}/pdf")
def exportar_pdf_base(
    proceso_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("tecnico", "admin"))],
) -> dict:
    proceso = _load_proceso(db, proceso_id)
    snapshot = _build_snapshot(db, proceso["beneficiario_id"])
    db.execute(
        """
        UPDATE procesos_tecnicos
        SET pdf_snapshot_json = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (str(snapshot), proceso_id),
    )
    return {
        "proceso_id": proceso_id,
        "pdf": {
            "status": "base_ready",
            "generated_at": _utc_now_iso(),
            "snapshot_included": True,
        },
    }


@router.get("/admin/tecnica/revisiones-pendientes")
def listar_revisiones_pendientes_admin(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> dict:
    rows = db.execute(
        """
        SELECT
            pt.id AS proceso_id,
            pt.beneficiario_id,
            b.nombre,
            b.folio,
            pt.estado,
            pt.revision_pendiente,
            pt.updated_at
        FROM procesos_tecnicos pt
        JOIN beneficiarios b ON b.id = pt.beneficiario_id
        WHERE pt.revision_pendiente = TRUE
        ORDER BY pt.updated_at DESC
        """
    ).fetchall()
    return {"items": rows, "total": len(rows)}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload-foto")
async def upload_foto(
    foto: UploadFile = File(...),
    _usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin", "organizacion"))] = None,
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


@router.post("/solicitudes", status_code=201, response_model=SolicitudCreateResponse)
def crear_solicitud(
    body: SolicitudCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin", "organizacion"))],
) -> SolicitudCreateResponse:
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
                 soporte_oxigeno, observaciones_posturales, altura_total_in, peso_kg,
                 medida_cabeza_asiento, medida_hombro_asiento, medida_prof_asiento,
                 medida_rodilla_talon, medida_ancho_cadera, unidad_captura, unidad_peso_captura, foto_url,
                 entidad_solicitante, prioridad, justificacion, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.beneficiario_id,
                usuario.usuario_id,
                body.entorno,
                body.control_tronco,
                body.control_cabeza,
                body.control_de_piernas,
                body.soporte_oxigeno,
                body.observaciones_posturales,
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

    assert_resource_owner(row["usuario_id"], usuario)

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
    return out


@router.patch("/solicitudes/{id}", response_model=SolicitudUpdateResponse)
def actualizar_solicitud(
    id: int,
    body: SolicitudUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "tecnico", "admin", "organizacion"))],
) -> SolicitudUpdateResponse:
    existing = db.execute(
        """SELECT id, usuario_id, beneficiario_id,
                  unidad_captura, unidad_peso_captura,
                  altura_total_in, medida_cabeza_asiento, medida_hombro_asiento,
                  medida_prof_asiento, medida_rodilla_talon, medida_ancho_cadera,
                  peso_kg
           FROM solicitudes_tecnicas WHERE id = %s""", (id,)
    ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    assert_resource_owner(existing["usuario_id"], usuario)

    fields = body.model_dump(exclude_none=True)
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
    elif fields.get("status") == "completo" and "unidad_medida" not in fields:
        # Finalizing without body-provided measurement unit: use the stored capture unit to
        # convert measurement values to canonical inches/lb so they are not silently promoted
        # with the wrong unit.
        # For each measurement column: if the body provided a value, convert that; otherwise
        # if the stored DB value needs conversion, promote it so the stored canonical value is
        # correct after this PATCH.
        stored_unidad = existing["unidad_captura"] or "in"
        stored_unidad_peso = existing["unidad_peso_captura"] or "lb"
        _MEASURE_COLS = (
            "altura_total_in", "medida_cabeza_asiento", "medida_hombro_asiento",
            "medida_prof_asiento", "medida_rodilla_talon", "medida_ancho_cadera",
        )
        if stored_unidad == "cm":
            for col in _MEASURE_COLS:
                if col in fields:
                    # Body provided a value in cm — convert it
                    if fields[col] is not None:
                        fields[col] = _to_inches(Decimal(str(fields[col])), "cm")
                else:
                    # No body value; convert the stored DB value and include it in UPDATE
                    raw = existing[col]
                    if raw is not None:
                        fields[col] = _to_inches(Decimal(str(raw)), "cm")
        if stored_unidad_peso == "kg":
            if "peso_kg" in fields:
                if fields["peso_kg"] is not None:
                    fields["peso_kg"] = _to_kg(Decimal(str(fields["peso_kg"])), "kg")
            else:
                raw_peso = existing["peso_kg"]
                if raw_peso is not None:
                    fields["peso_kg"] = _to_kg(Decimal(str(raw_peso)), "kg")
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


def _to_kg(v: Optional[Decimal], unidad: str) -> Optional[Decimal]:
    """Convert a weight value to pounds (canonical storage unit).

    If the capture unit is 'kg', multiply by 2.20462 (1 kg ≈ 2.20462 lb)
    and quantize to 3 decimal places. Otherwise return unchanged.
    """
    if v is None:
        return None
    if unidad == "kg":
        lb = v * Decimal("2.20462")
        return lb.quantize(Decimal("0.001"))
    return v  # already lb


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
) -> dict:
    if usuario.rol not in {"capturista", "tecnico", "admin", "organizacion"}:
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
