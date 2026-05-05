import os
import uuid
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from supabase import create_client

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, assert_resource_owner, require_roles

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


def _build_list_where_clause(
    *,
    q: Optional[str],
    sede: Optional[str],
    estado: Optional[str],
    revision_pendiente: Optional[bool],
) -> tuple[str, list]:
    clauses: list[str] = ["1=1"]
    params: list = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        clauses.append("(b.nombre ILIKE %s OR b.folio ILIKE %s)")
        params.extend([term, term])

    if sede and sede.strip():
        clauses.append("COALESCE(e.sede, '') = %s")
        params.append(sede.strip())

    if estado and estado.strip():
        if estado not in _PROCESS_STATES:
            raise HTTPException(
                status_code=422,
                detail={"type": "invalid_filter", "message": "estado no válido"},
            )
        clauses.append("COALESCE(pt.estado, 'sin_iniciar') = %s")
        params.append(estado)

    if revision_pendiente is not None:
        clauses.append("COALESCE(pt.revision_pendiente, FALSE) = %s")
        params.append(revision_pendiente)

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
        db.execute("SELECT * FROM beneficiarios WHERE id = %s", (beneficiario_id,)).fetchone()
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
    altura_total_in: Optional[float] = None
    peso_kg: Optional[float] = None
    medida_cabeza_asiento: Optional[float] = None
    medida_hombro_asiento: Optional[float] = None
    medida_prof_asiento: Optional[float] = None
    medida_rodilla_talon: Optional[float] = None
    medida_ancho_cadera: Optional[float] = None
    foto_path: Optional[str] = None
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
    foto_path: Optional[str] = None
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
) -> dict:
    where_clause, params = _build_list_where_clause(
        q=q,
        sede=sede,
        estado=estado,
        revision_pendiente=revision_pendiente,
    )
    rows = db.execute(
        f"""
        SELECT
            b.id AS beneficiario_id,
            b.nombre,
            b.folio,
            COALESCE(e.sede, '') AS sede,
            COALESCE(pt.estado, 'sin_iniciar') AS estado,
            COALESCE(pt.revision_pendiente, FALSE) AS revision_pendiente,
            pt.id AS proceso_id
        FROM beneficiarios b
        LEFT JOIN estudios_socioeconomicos e ON e.beneficiario_id = b.id
        LEFT JOIN procesos_tecnicos pt ON pt.beneficiario_id = b.id
        WHERE {where_clause}
        ORDER BY b.nombre ASC
        """,
        tuple(params),
    ).fetchall()
    return {"items": rows, "total": len(rows)}


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
                 medida_rodilla_talon, medida_ancho_cadera, foto_url,
                 entidad_solicitante, prioridad, justificacion, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
