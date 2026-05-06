"""
Estudio socioeconómico router (v2).

Changes from v1:
- Uses Depends(get_db) instead of context manager
- Uses require_auth (JWT) — identity via usuario.usuario_id (v2)
- region_id + sede at top level of EstudioCreateRequest (moved from EstudioIn)
- Calls generate_folio() to assign structured folio to each beneficiario
- Returns folio in EstudioCreateResponse
"""

import os
import re
import uuid
from typing import Annotated, Optional
from urllib.parse import urlparse, unquote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator
from supabase import create_client

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, assert_resource_owner, require_roles
from routers.regiones import generate_folio

router = APIRouter()
ALLOWED_ESTADO_CIVIL = {"Casado", "Soltero", "Viudo"}
_DOCUMENT_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_DOCUMENT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
_DOCUMENT_MAX_SIZE_BYTES = 10 * 1024 * 1024
_DOCUMENT_BUCKET = "documentos-estudio"
_DOCUMENT_STORAGE_URL_PREFIX = f"storage://{_DOCUMENT_BUCKET}/"
_DOCUMENT_TYPES = {"credencial", "comprobante_domicilio"}
_DOCUMENT_SIGNED_URL_TTL_SECONDS = 60


def _storage():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    ).storage.from_(_DOCUMENT_BUCKET)


def extract_document_path(raw_value: Optional[str]) -> Optional[str]:
    if raw_value is None:
        return None

    value = raw_value.strip()
    if not value:
        return None

    if value.startswith(_DOCUMENT_STORAGE_URL_PREFIX):
        path = value[len(_DOCUMENT_STORAGE_URL_PREFIX):]
        return path or None

    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        marker = f"/{_DOCUMENT_BUCKET}/"
        if marker not in parsed.path:
            return None
        return unquote(parsed.path.split(marker, 1)[1]) or None

    return None


def _derive_document_url(document_path: Optional[str]) -> Optional[str]:
    if document_path is None:
        return None
    return f"{_DOCUMENT_STORAGE_URL_PREFIX}{document_path}"


def _resolve_document_refs(*, document_path: Optional[str], document_url: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    canonical_path = extract_document_path(document_path) or extract_document_path(document_url)
    derived_url = _derive_document_url(canonical_path)
    return canonical_path, derived_url


def _signed_url_from_response(payload: object) -> Optional[str]:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return payload.get("signedURL") or payload.get("signedUrl") or payload.get("url")
    return None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BeneficiarioIn(BaseModel):
    nombre: str
    fecha_nacimiento: str
    diagnostico: str
    calle: str
    colonia: str
    ciudad: str
    telefonos: str
    email: Optional[str] = None

    @field_validator("telefonos")
    @classmethod
    def telefonos_valido(cls, v: str) -> str:
        telefono = v.strip()
        if not re.fullmatch(r"^[0-9]{10}$", telefono):
            raise ValueError("El teléfono debe contener exactamente 10 dígitos numéricos")
        return telefono


class TutorIn(BaseModel):
    numero_tutor: int
    nombre: str
    edad: Optional[int] = None
    nivel_estudios: Optional[str] = None
    estado_civil: Optional[str] = None
    num_hijos: Optional[int] = None
    vivienda: Optional[str] = None
    fuente_empleo: Optional[str] = None
    antiguedad: Optional[str] = None
    ingreso_mensual: Optional[float] = None
    tiene_imss: bool = False
    tiene_infonavit: bool = False

    @field_validator("numero_tutor")
    @classmethod
    def numero_tutor_valido(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError("numero_tutor debe ser 1 o 2")
        return v

    @field_validator("estado_civil")
    @classmethod
    def estado_civil_valido(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        if v not in ALLOWED_ESTADO_CIVIL:
            raise ValueError("estado_civil solo permite Casado, Soltero, Viudo o vacío")
        return v


class EstudioIn(BaseModel):
    otras_fuentes_ingreso: Optional[str] = None
    monto_otras_fuentes: Optional[float] = None
    tuvo_silla_previa: bool
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: str
    fecha_estudio: str
    status: str = "borrador"
    credencial_path: Optional[str] = None
    credencial_url: Optional[str] = None
    comprobante_domicilio_path: Optional[str] = None
    comprobante_domicilio_url: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: str) -> str:
        if v not in ("borrador", "completo"):
            raise ValueError("status debe ser 'borrador' o 'completo'")
        return v


class EstudioCreateRequest(BaseModel):
    """
    Top-level request for creating a full estudio socioeconómico.

    Note: region_id and sede are set here (not inside estudio) because they
    describe WHEN and WHERE the registration happens, not the study itself.
    """
    region_id: int
    sede: str
    beneficiario: BeneficiarioIn
    tutores: list[TutorIn]
    estudio: EstudioIn


class EstudioCreateResponse(BaseModel):
    estudio_id: int
    beneficiario_id: int
    folio: str
    status: str


class EstudioUpdateRequest(BaseModel):
    otras_fuentes_ingreso: Optional[str] = None
    monto_otras_fuentes: Optional[float] = None
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    fecha_estudio: Optional[str] = None
    status: Optional[str] = None
    tutores: Optional[list[TutorIn]] = None
    credencial_path: Optional[str] = None
    credencial_url: Optional[str] = None
    comprobante_domicilio_path: Optional[str] = None
    comprobante_domicilio_url: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("borrador", "completo"):
            raise ValueError("status debe ser 'borrador' o 'completo'")
        return v


class EstudioUpdateResponse(BaseModel):
    estudio_id: int
    status: str
    updated_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload-documento")
async def upload_documento_estudio(
    tipo: str = Form(...),
    archivo: UploadFile = File(...),
    _usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin"))] = None,
) -> dict:
    if tipo not in _DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail="Tipo de documento no permitido")

    if archivo.content_type not in _DOCUMENT_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    _, ext = os.path.splitext(archivo.filename or "")
    if ext.lower() not in _DOCUMENT_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    data = await archivo.read()
    if len(data) > _DOCUMENT_MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="El archivo excede 10MB")

    filename = f"{tipo}/{uuid.uuid4()}{ext.lower()}"

    try:
        _storage().upload(
            path=filename,
            file=data,
            file_options={"content-type": archivo.content_type},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error al subir el documento") from exc

    return {
        "tipo": tipo,
        "documento_path": filename,
        "documento_url": _derive_document_url(filename),
    }


@router.get("/documentos")
def ver_documento_estudio(
    path: str = Query(...),
    _usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin"))] = None,
):
    document_path = extract_document_path(path) or path.strip()
    if not document_path:
        raise HTTPException(status_code=400, detail="Documento inválido")

    try:
        signed_raw = _storage().create_signed_url(document_path, _DOCUMENT_SIGNED_URL_TTL_SECONDS)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Documento no disponible") from exc

    signed_url = _signed_url_from_response(signed_raw)
    if not signed_url:
        raise HTTPException(status_code=500, detail="No se pudo generar URL firmada")

    return RedirectResponse(url=signed_url, status_code=307)

@router.post("/estudios", status_code=201, response_model=EstudioCreateResponse)
def crear_estudio(
    body: EstudioCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin"))],
) -> EstudioCreateResponse:
    """Create a complete estudio socioeconómico with beneficiario, tutores, and study data."""
    _validar_tutores(body.tutores)
    credencial_path, credencial_url = _resolve_document_refs(
        document_path=body.estudio.credencial_path,
        document_url=body.estudio.credencial_url,
    )
    comprobante_path, comprobante_url = _resolve_document_refs(
        document_path=body.estudio.comprobante_domicilio_path,
        document_url=body.estudio.comprobante_domicilio_url,
    )

    # 1. Generate structured folio (atomic counter per region/year)
    folio = generate_folio(db, body.region_id)

    # 2. INSERT beneficiario (with folio + region + sede)
    beneficiario_id = db.execute(
        """
        INSERT INTO beneficiarios
            (nombre, fecha_nacimiento, diagnostico, calle, colonia, ciudad,
             telefonos, email, folio, region_id, sede)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            body.beneficiario.nombre,
            body.beneficiario.fecha_nacimiento,
            body.beneficiario.diagnostico,
            body.beneficiario.calle,
            body.beneficiario.colonia,
            body.beneficiario.ciudad,
            body.beneficiario.telefonos,
            body.beneficiario.email,
            folio,
            body.region_id,
            body.sede,
        ),
    ).fetchone()["id"]

    # 3. INSERT tutores
    _insertar_tutores(db, beneficiario_id, body.tutores)

    # 4. INSERT estudio (usuario_id from JWT claims)
    estudio = body.estudio
    estudio_id = db.execute(
        """
        INSERT INTO estudios_socioeconomicos
            (beneficiario_id, usuario_id, otras_fuentes_ingreso,
             monto_otras_fuentes, tuvo_silla_previa, como_obtuvo_silla,
             elaboro_estudio, fecha_estudio, sede, status,
             credencial_path, credencial_url,
             comprobante_domicilio_path, comprobante_domicilio_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            beneficiario_id,
            usuario.usuario_id,
            estudio.otras_fuentes_ingreso,
            estudio.monto_otras_fuentes,
            int(estudio.tuvo_silla_previa) if estudio.tuvo_silla_previa is not None else None,
            estudio.como_obtuvo_silla,
            estudio.elaboro_estudio,
            estudio.fecha_estudio,
            body.sede,
            estudio.status,
            credencial_path,
            credencial_url,
            comprobante_path,
            comprobante_url,
        ),
    ).fetchone()["id"]

    return EstudioCreateResponse(
        estudio_id=estudio_id,
        beneficiario_id=beneficiario_id,
        folio=folio,
        status=estudio.status,
    )


@router.get("/estudios/{id}")
def obtener_estudio(
    id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin"))],
) -> dict:
    """Retrieve a full estudio by ID. Only the owner or an admin may read it."""
    estudio_row = db.execute(
        "SELECT * FROM estudios_socioeconomicos WHERE id = %s", (id,)
    ).fetchone()

    if estudio_row is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    assert_resource_owner(estudio_row["usuario_id"], usuario)

    beneficiario_row = db.execute(
        "SELECT * FROM beneficiarios WHERE id = %s",
        (estudio_row["beneficiario_id"],),
    ).fetchone()

    tutores_rows = db.execute(
        "SELECT * FROM tutores WHERE beneficiario_id = %s ORDER BY numero_tutor",
        (estudio_row["beneficiario_id"],),
    ).fetchall()

    result = dict(estudio_row)
    result["beneficiario"] = dict(beneficiario_row)
    result["tutores"] = [dict(t) for t in tutores_rows]

    return result


@router.patch("/estudios/{id}", response_model=EstudioUpdateResponse)
def actualizar_estudio(
    id: int,
    body: EstudioUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin"))],
) -> EstudioUpdateResponse:
    """Partial update of an estudio. Only the owner or an admin may update it."""
    existing = db.execute(
        "SELECT id, usuario_id, beneficiario_id FROM estudios_socioeconomicos WHERE id = %s", (id,)
    ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    assert_resource_owner(existing["usuario_id"], usuario)

    if body.tutores is not None:
        _validar_tutores(body.tutores)
        db.execute("DELETE FROM tutores WHERE beneficiario_id = %s", (existing["beneficiario_id"],))
        _insertar_tutores(db, existing["beneficiario_id"], body.tutores)

    fields = body.model_dump(exclude_none=True, exclude={"tutores"})

    credencial_path, credencial_url = _resolve_document_refs(
        document_path=fields.pop("credencial_path", None),
        document_url=fields.get("credencial_url"),
    )
    if credencial_path is not None:
        fields["credencial_path"] = credencial_path
    if credencial_url is not None:
        fields["credencial_url"] = credencial_url

    comprobante_path, comprobante_url = _resolve_document_refs(
        document_path=fields.pop("comprobante_domicilio_path", None),
        document_url=fields.get("comprobante_domicilio_url"),
    )
    if comprobante_path is not None:
        fields["comprobante_domicilio_path"] = comprobante_path
    if comprobante_url is not None:
        fields["comprobante_domicilio_url"] = comprobante_url

    if not fields:
        row = db.execute(
            "SELECT id, status, updated_at FROM estudios_socioeconomicos WHERE id = %s",
            (id,),
        ).fetchone()
        return EstudioUpdateResponse(
            estudio_id=row["id"],
            status=row["status"],
            updated_at=row["updated_at"].isoformat(),
        )

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    values.append(id)

    db.execute(
        f"UPDATE estudios_socioeconomicos SET {set_clause}, updated_at = NOW() WHERE id = %s",
        values,
    )

    row = db.execute(
        "SELECT id, status, updated_at FROM estudios_socioeconomicos WHERE id = %s",
        (id,),
    ).fetchone()

    return EstudioUpdateResponse(
        estudio_id=row["id"],
        status=row["status"],
        updated_at=row["updated_at"].isoformat(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validar_tutores(tutores: list[TutorIn]) -> None:
    if not tutores:
        raise HTTPException(status_code=400, detail="Se requiere al menos un tutor")
    numeros = [t.numero_tutor for t in tutores]
    if len(numeros) != len(set(numeros)):
        raise HTTPException(status_code=400, detail="No se pueden repetir los números de tutor")
    for num in numeros:
        if num not in (1, 2):
            raise HTTPException(status_code=400, detail=f"numero_tutor inválido: {num}")


def _insertar_tutores(db: _DBAdapter, beneficiario_id: int, tutores: list[TutorIn]) -> None:
    for tutor in tutores:
        db.execute(
            """
            INSERT INTO tutores
                (beneficiario_id, numero_tutor, nombre, edad, nivel_estudios,
                 estado_civil, num_hijos, vivienda, fuente_empleo, antiguedad,
                 ingreso_mensual, tiene_imss, tiene_infonavit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                beneficiario_id,
                tutor.numero_tutor,
                tutor.nombre,
                tutor.edad,
                tutor.nivel_estudios or None,
                tutor.estado_civil,
                tutor.num_hijos if tutor.num_hijos is not None else 0,
                tutor.vivienda or None,
                tutor.fuente_empleo or None,
                tutor.antiguedad or None,
                tutor.ingreso_mensual,
                int(tutor.tiene_imss),
                int(tutor.tiene_infonavit),
            ),
        )
