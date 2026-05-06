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
from pydantic import BaseModel, field_validator, model_validator
from supabase import create_client

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, assert_resource_owner, require_roles
from routers.regiones import generate_folio
from utils.text import normalize_text

router = APIRouter()
ESTADO_CIVIL_CATALOG = {"SOLTERO", "CASADO", "VIUDO", "DIVORCIADO", "UNION_LIBRE"}
TRIESTADO_CATALOG = frozenset({"SI", "NO", "NO_APLICA"})
VIVIENDA_CATALOG = {"PROPIA", "RENTADA", "PRESTADA", "FAMILIAR", "INFORMAL", "OTRA"}
NIVEL_ESTUDIOS_CATALOG = frozenset({"NINGUNO", "PRIMARIA", "SECUNDARIA", "BACHILLERATO", "LICENCIATURA", "MAESTRIA", "DOCTORADO", "TECNICO"})
COMO_OBTUVO_SILLA_CATALOG = frozenset({"COMPRA", "DONACION"})
ESTADOS_INEGI = {
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32"
}
ESTADOS_INEGI_NOMBRES = {
    "01": "AGUASCALIENTES", "02": "BAJA CALIFORNIA", "03": "BAJA CALIFORNIA SUR", "04": "CAMPECHE",
    "05": "COAHUILA", "06": "COLIMA", "07": "CHIAPAS", "08": "CHIHUAHUA", "09": "CIUDAD DE MEXICO",
    "10": "DURANGO", "11": "GUANAJUATO", "12": "GUERRERO", "13": "HIDALGO", "14": "JALISCO",
    "15": "ESTADO DE MEXICO", "16": "MICHOACAN", "17": "MORELOS", "18": "NAYARIT", "19": "NUEVO LEON",
    "20": "OAXACA", "21": "PUEBLA", "22": "QUERETARO", "23": "QUINTANA ROO", "24": "SAN LUIS POTOSI",
    "25": "SINALOA", "26": "SONORA", "27": "TABASCO", "28": "TAMAULIPAS", "29": "TLAXCALA",
    "30": "VERACRUZ", "31": "YUCATAN", "32": "ZACATECAS",
}
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
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    fecha_nacimiento: str
    diagnostico: str
    calle: str
    num_ext: Optional[str] = None
    num_int: Optional[str] = None
    colonia: str
    ciudad: str
    estado_codigo: str
    estado_nombre: Optional[str] = None
    sexo: str
    telefonos: str
    email: Optional[str] = None

    @field_validator("telefonos")
    @classmethod
    def telefonos_valido(cls, v: str) -> str:
        telefono = re.sub(r"\D", "", v or "")
        if not re.fullmatch(r"^[0-9]{10}$", telefono):
            raise ValueError("El teléfono debe contener exactamente 10 dígitos numéricos")
        return telefono

    @field_validator("estado_codigo")
    @classmethod
    def estado_codigo_valido(cls, v: str) -> str:
        code = normalize_text(v)
        if code not in ESTADOS_INEGI:
            raise ValueError("estado_codigo fuera de catálogo INEGI")
        return code

    @field_validator("sexo")
    @classmethod
    def sexo_valido(cls, v: str) -> str:
        sexo = normalize_text(v)
        if sexo not in {"M", "F", "NE"}:
            raise ValueError("sexo debe ser M, F o NE")
        return sexo

    @field_validator("nombres", "apellido_paterno", "apellido_materno",
                      "diagnostico", "calle", "colonia", "ciudad", mode="before")
    @classmethod
    def normalizar_textos_principales(cls, v: Optional[str]) -> Optional[str]:
        return normalize_text(v)

    @field_validator("nombres")
    @classmethod
    def validar_nombres(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 60:
            raise ValueError("nombres debe tener entre 2 y 60 caracteres")
        if not re.fullmatch(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$", v):
            raise ValueError("nombres contiene caracteres no permitidos")
        return v

    @field_validator("apellido_paterno")
    @classmethod
    def validar_apellido_paterno(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 40:
            raise ValueError("apellido_paterno debe tener entre 2 y 40 caracteres")
        if not re.fullmatch(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$", v):
            raise ValueError("apellido_paterno contiene caracteres no permitidos")
        return v

    @field_validator("apellido_materno")
    @classmethod
    def validar_apellido_materno(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 40:
            raise ValueError("apellido_materno debe tener entre 2 y 40 caracteres")
        if not re.fullmatch(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$", v):
            raise ValueError("apellido_materno contiene caracteres no permitidos")
        return v

    @field_validator("diagnostico")
    @classmethod
    def diagnostico_valido(cls, v: str) -> str:
        if len(v) < 3 or len(v) > 160:
            raise ValueError("diagnostico debe tener entre 3 y 160 caracteres")
        return v

    @field_validator("calle", "colonia")
    @classmethod
    def direccion_texto_valido(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 120:
            raise ValueError("campo de dirección debe tener entre 2 y 120 caracteres")
        return v

    @field_validator("ciudad")
    @classmethod
    def ciudad_valida(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 80:
            raise ValueError("ciudad debe tener entre 2 y 80 caracteres")
        return v

    @field_validator("num_ext", "num_int", mode="before")
    @classmethod
    def validar_numero_domicilio(cls, v: Optional[str]) -> Optional[str]:
        value = normalize_text(v)
        if value is None:
            return None
        if not re.fullmatch(r"^[A-Z0-9\-/]+$", value):
            raise ValueError("solo se permiten letras, números, guion y diagonal")
        if len(value) > 10:
            raise ValueError("longitud máxima 10 caracteres")
        return value

    @field_validator("estado_nombre", mode="before")
    @classmethod
    def normalizar_estado_nombre(cls, v: Optional[str]) -> Optional[str]:
        return normalize_text(v)

    @field_validator("estado_nombre")
    @classmethod
    def estado_nombre_consistente(cls, v: Optional[str], info) -> Optional[str]:
        if not v:
            return v
        code = info.data.get("estado_codigo")
        if code and ESTADOS_INEGI_NOMBRES.get(code) != v:
            raise ValueError("estado_nombre no corresponde a estado_codigo")
        return v


class TutorIn(BaseModel):
    numero_tutor: int
    nombre: str
    edad: Optional[int] = None
    nivel_estudios: Optional[str] = None
    estado_civil: Optional[str] = None
    num_hijos: Optional[int] = None
    vivienda: Optional[str] = None
    fuente_empleo: Optional[str] = None
    antiguedad_anios: Optional[int] = 0
    antiguedad_meses_extra: Optional[int] = 0
    antiguedad_aplica: bool = True
    ingreso_mensual: Optional[int] = None
    sin_empleo: bool = False
    otras_fuentes_aplica: bool = False
    otras_fuentes_ingreso: Optional[str] = None
    monto_otras_fuentes: Optional[float] = None
    imss_estatus:      Optional[str] = None   # replaced: tiene_imss: bool = False
    infonavit_estatus: Optional[str] = None   # replaced: tiene_infonavit: bool = False

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
        vv = normalize_text(v)
        if vv not in ESTADO_CIVIL_CATALOG:
            raise ValueError("estado_civil fuera de catálogo")
        return vv

    @field_validator("vivienda")
    @classmethod
    def vivienda_valida(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        vv = normalize_text(v)
        if vv not in VIVIENDA_CATALOG:
            raise ValueError("vivienda fuera de catálogo")
        return vv

    @field_validator("edad")
    @classmethod
    def edad_valida(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 18:
            raise ValueError("edad del tutor debe ser mínimo 18")
        return v

    @field_validator("nombre", "nivel_estudios", "fuente_empleo", "otras_fuentes_ingreso", mode="before")
    @classmethod
    def normalizar_textos_tutor(cls, v: Optional[str]) -> Optional[str]:
        return normalize_text(v)

    @field_validator("nivel_estudios")
    @classmethod
    def nivel_estudios_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in NIVEL_ESTUDIOS_CATALOG:
            raise ValueError("nivel_estudios fuera de catálogo")
        return v

    @field_validator("ingreso_mensual")
    @classmethod
    def ingreso_mensual_valido(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 9999999):
            raise ValueError("monto fuera de rango permitido")
        return v

    @field_validator("monto_otras_fuentes")
    @classmethod
    def monto_otras_fuentes_valido(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 999999):
            raise ValueError("monto fuera de rango permitido")
        return v

    @field_validator("num_hijos")
    @classmethod
    def num_hijos_valido(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 30):
            raise ValueError("num_hijos debe estar entre 0 y 30")
        return v

    @field_validator("imss_estatus", "infonavit_estatus")
    @classmethod
    def triestado_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        vv = normalize_text(v)
        if vv not in TRIESTADO_CATALOG:
            raise ValueError("el estatus debe ser SI, NO o NO_APLICA")
        return vv

    @model_validator(mode="before")
    @classmethod
    def backward_compat_imss_infonavit(cls, data: dict) -> dict:
        """Map legacy boolean tiene_imss/tiene_infonavit to new imss_estatus/infonavit_estatus."""
        if isinstance(data, dict):
            # Only apply backward compat if the new fields are NOT present
            if "imss_estatus" not in data and "tiene_imss" in data:
                raw = data.pop("tiene_imss")
                data["imss_estatus"] = "SI" if raw in (True, 1) else "NO" if raw in (False, 0) else None
            if "infonavit_estatus" not in data and "tiene_infonavit" in data:
                raw = data.pop("tiene_infonavit")
                data["infonavit_estatus"] = "SI" if raw in (True, 1) else "NO" if raw in (False, 0) else None
        return data

    @field_validator("antiguedad_anios")
    @classmethod
    def antiguedad_anios_valida(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 50):
            raise ValueError("antiguedad_anios debe estar entre 0 y 50")
        return v

    @field_validator("antiguedad_meses_extra")
    @classmethod
    def antiguedad_meses_valida(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 11):
            raise ValueError("antiguedad_meses_extra debe estar entre 0 y 11")
        return v


class EstudioIn(BaseModel):
    tuvo_silla_previa: bool
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    ciudad_registro: Optional[str] = None
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

    @field_validator("como_obtuvo_silla", "ciudad_registro", mode="before")
    @classmethod
    def normalizar_textos_estudio(cls, v: Optional[str]) -> Optional[str]:
        return normalize_text(v)


class EstudioCreateRequest(BaseModel):
    """
    Top-level request for creating a full estudio socioeconómico.

    Note: region_id and sede are set here (not inside estudio) because they
    describe WHEN and WHERE the registration happens, not the study itself.
    """
    region_id: int
    sede: str
    ciudad_registro: str
    beneficiario: BeneficiarioIn
    tutores: list[TutorIn]
    estudio: EstudioIn


class EstudioCreateResponse(BaseModel):
    estudio_id: int
    beneficiario_id: int
    folio: str
    status: str


class EstudioUpdateRequest(BaseModel):
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    ciudad_registro: Optional[str] = None
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

    # 2. Compose canonical nombre from normalized structured fields
    b = body.beneficiario
    nombre_composed = f"{b.nombres} {b.apellido_paterno} {b.apellido_materno}"

    # 3. INSERT beneficiario (with folio + region + sede + structured name)
    beneficiario_id = db.execute(
        """
        INSERT INTO beneficiarios
             (nombre, nombres, apellido_paterno, apellido_materno,
              fecha_nacimiento, diagnostico, calle, num_ext, num_int, colonia, ciudad,
              estado_codigo, estado_nombre, sexo,
              telefonos, email, folio, region_id, sede)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            nombre_composed,
            b.nombres,
            b.apellido_paterno,
            b.apellido_materno,
            b.fecha_nacimiento,
            b.diagnostico,
            b.calle,
            b.num_ext,
            b.num_int,
            b.colonia,
            b.ciudad,
            b.estado_codigo,
            b.estado_nombre,
            b.sexo,
            b.telefonos,
            b.email,
            folio,
            body.region_id,
            body.sede,
        ),
    ).fetchone()["id"]

    # 4. INSERT tutores
    _insertar_tutores(db, beneficiario_id, body.tutores)

    # 5. INSERT estudio (usuario_id from JWT claims)
    estudio = body.estudio
    estudio_id = db.execute(
        """
        INSERT INTO estudios_socioeconomicos
            (beneficiario_id, usuario_id, otras_fuentes_ingreso,
             monto_otras_fuentes, tuvo_silla_previa, como_obtuvo_silla,
             elaboro_estudio, fecha_estudio, sede, ciudad_registro, status,
             credencial_path, credencial_url,
             comprobante_domicilio_path, comprobante_domicilio_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            beneficiario_id,
            usuario.usuario_id,
            None,
            None,
            int(estudio.tuvo_silla_previa) if estudio.tuvo_silla_previa is not None else None,
            _resolve_como_obtuvo_silla(estudio.tuvo_silla_previa, estudio.como_obtuvo_silla),
            usuario.nombre,
            estudio.fecha_estudio,
            body.sede,
            body.ciudad_registro,
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
    result["tutores"] = [
        _tutor_response(dict(t)) for t in tutores_rows
    ]

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

    fields = body.model_dump(exclude_none=True, exclude={"tutores", "elaboro_estudio", "ciudad_registro"})
    fields["elaboro_estudio"] = usuario.nombre
    if "tuvo_silla_previa" in fields:
        fields["como_obtuvo_silla"] = _resolve_como_obtuvo_silla(fields["tuvo_silla_previa"], fields.get("como_obtuvo_silla"))

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

def _tutor_response(t: dict) -> dict:
    """Transform a DB tutor row into API response format.
    
    Renames tiene_imss/tiene_infonavit INTEGER columns to
    imss_estatus/infonavit_estatus STRING fields.
    Converts ingreso_mensual from REAL to int for API consistency.
    """
    t["imss_estatus"] = _mapear_de_db(t.pop("tiene_imss", None))
    t["infonavit_estatus"] = _mapear_de_db(t.pop("tiene_infonavit", None))
    # Convert REAL to int for API consistency (RF-03)
    if t.get("ingreso_mensual") is not None:
        t["ingreso_mensual"] = int(t["ingreso_mensual"])
    return t


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
                 ingreso_mensual, tiene_imss, tiene_infonavit,
                 antiguedad_meses, antiguedad_aplica, sin_empleo,
                 otras_fuentes_aplica, otras_fuentes_ingreso, monto_otras_fuentes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                None if tutor.sin_empleo else (tutor.fuente_empleo or None),
                None,
                0 if tutor.sin_empleo else tutor.ingreso_mensual,
                _mapear_a_db(tutor.imss_estatus),
                _mapear_a_db(tutor.infonavit_estatus),
                _calc_antiguedad_meses(tutor),
                int(tutor.antiguedad_aplica),
                int(tutor.sin_empleo),
                int(tutor.otras_fuentes_aplica),
                tutor.otras_fuentes_ingreso if tutor.otras_fuentes_aplica else None,
                tutor.monto_otras_fuentes if tutor.otras_fuentes_aplica else None,
            ),
        )


def _resolve_como_obtuvo_silla(tuvo_silla_previa: bool, como_obtuvo_silla: Optional[str]) -> Optional[str]:
    if not tuvo_silla_previa:
        return None
    val = normalize_text(como_obtuvo_silla)
    if not val:
        raise HTTPException(status_code=422, detail="como_obtuvo_silla es obligatorio cuando tuvo_silla_previa=true")
    if val not in COMO_OBTUVO_SILLA_CATALOG:
        raise HTTPException(status_code=422, detail="como_obtuvo_silla no pertenece al catálogo")
    return val


def _mapear_a_db(valor: Optional[str]) -> Optional[int]:
    """Map triestado string to DB integer: SI→1, NO→0, NO_APLICA→NULL, None→NULL."""
    if valor is None:
        return None
    mapping: dict[str, Optional[int]] = {"SI": 1, "NO": 0, "NO_APLICA": None}
    return mapping.get(valor)


def _mapear_de_db(valor: Optional[int]) -> str:
    """Map DB integer to triestado string: 1→SI, 0→NO, NULL→NO_APLICA."""
    if valor is None:
        return "NO_APLICA"
    return "SI" if valor == 1 else "NO"


def _calc_antiguedad_meses(tutor: TutorIn) -> Optional[int]:
    if not tutor.antiguedad_aplica:
        return None
    anios = tutor.antiguedad_anios or 0
    meses = tutor.antiguedad_meses_extra or 0
    return (anios * 12) + meses
