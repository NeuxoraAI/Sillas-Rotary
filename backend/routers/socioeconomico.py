"""
Estudio socioeconómico router (v2).

Changes from v1:
- Uses Depends(get_db) instead of context manager
- Uses require_auth (JWT) — identity via usuario.usuario_id (v2)
- region_id + sede at top level of EstudioCreateRequest (moved from EstudioIn)
- Calls generate_folio() to assign structured folio to each beneficiario
- Returns folio in EstudioCreateResponse
"""

from typing import Annotated, Optional
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, assert_resource_owner, require_roles
from routers.regiones import generate_folio
from utils.text import normalize_text
from validators import (
    validate_nombre,
    validate_apellido,
    validate_diagnostico,
    validate_calle,
    validate_colonia,
    validate_ciudad,
    validate_numero_domicilio,
    validate_telefono,
    validate_estado_codigo,
    validate_estado_nombre,
    validate_sexo,
    validate_catalog,
    validate_ingreso_mensual,
    validate_monto_otras_fuentes,
    validate_num_hijos,
    validate_edad,
    validate_antiguedad_anios,
    validate_antiguedad_meses,
    validate_numero_tutor,
    validate_fecha_nacimiento,
    validate_fecha_estudio,
    validate_status,
    validate_fuente_empleo,
    validate_otras_fuentes_ingreso,
    ESTADO_CIVIL_CATALOG,
    TRIESTADO_CATALOG,
    VIVIENDA_CATALOG,
    NIVEL_ESTUDIOS_CATALOG,
    COMO_OBTUVO_SILLA_CATALOG,
    ESTADOS_INEGI,
    ESTADOS_INEGI_NOMBRES,
    NUM_HIJOS_MAX,
)

router = APIRouter()


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

    @field_validator("fecha_nacimiento")
    @classmethod
    def _fecha_nacimiento_valida(cls, v: str) -> str:
        return validate_fecha_nacimiento(v)

    @field_validator("telefonos")
    @classmethod
    def _telefonos_valido(cls, v: str) -> str:
        return validate_telefono(v)

    @field_validator("estado_codigo")
    @classmethod
    def _estado_codigo_valido(cls, v: str) -> str:
        return validate_estado_codigo(v)

    @field_validator("sexo")
    @classmethod
    def _sexo_valido(cls, v: str) -> str:
        return validate_sexo(v)

    @field_validator("nombres", "apellido_paterno", "apellido_materno",
                      "diagnostico", "calle", "colonia", "ciudad", mode="before")
    @classmethod
    def _normalizar_textos_principales(cls, v: Optional[str]) -> Optional[str]:
        return normalize_text(v)

    @field_validator("nombres")
    @classmethod
    def _validar_nombres(cls, v: str) -> str:
        return validate_nombre(v)

    @field_validator("apellido_paterno")
    @classmethod
    def _validar_apellido_paterno(cls, v: str) -> str:
        return validate_apellido(v, "apellido_paterno")

    @field_validator("apellido_materno")
    @classmethod
    def _validar_apellido_materno(cls, v: str) -> str:
        return validate_apellido(v, "apellido_materno")

    @field_validator("diagnostico")
    @classmethod
    def _diagnostico_valido(cls, v: str) -> str:
        return validate_diagnostico(v)

    @field_validator("calle")
    @classmethod
    def _calle_valida(cls, v: str) -> str:
        return validate_calle(v)

    @field_validator("colonia")
    @classmethod
    def _colonia_valida(cls, v: str) -> str:
        return validate_colonia(v)

    @field_validator("ciudad")
    @classmethod
    def _ciudad_valida(cls, v: str) -> str:
        return validate_ciudad(v)

    @field_validator("num_ext", "num_int", mode="before")
    @classmethod
    def _validar_numero_domicilio(cls, v: Optional[str]) -> Optional[str]:
        return validate_numero_domicilio(v)

    @field_validator("estado_nombre", mode="before")
    @classmethod
    def _normalizar_estado_nombre(cls, v: Optional[str]) -> Optional[str]:
        return normalize_text(v)

    @field_validator("estado_nombre")
    @classmethod
    def _estado_nombre_consistente(cls, v: Optional[str], info) -> Optional[str]:
        return validate_estado_nombre(v, info.data.get("estado_codigo"))


class TutorIn(BaseModel):
    numero_tutor: int
    nombres: str
    apellido_paterno: str
    apellido_materno: str
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
    def _numero_tutor_valido(cls, v: int) -> int:
        return validate_numero_tutor(v)

    @field_validator("estado_civil")
    @classmethod
    def _estado_civil_valido(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        vv = normalize_text(v)
        return validate_catalog(vv, ESTADO_CIVIL_CATALOG, "estado_civil")

    @field_validator("vivienda")
    @classmethod
    def _vivienda_valida(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        vv = normalize_text(v)
        return validate_catalog(vv, VIVIENDA_CATALOG, "vivienda")

    @field_validator("edad")
    @classmethod
    def _edad_valida(cls, v: Optional[int]) -> Optional[int]:
        return validate_edad(v)

    @field_validator("nombres", "apellido_paterno", "apellido_materno",
                      "nivel_estudios", "fuente_empleo", "otras_fuentes_ingreso", mode="before")
    @classmethod
    def _normalizar_textos_tutor(cls, v: Optional[str]) -> Optional[str]:
        return normalize_text(v)

    @field_validator("nombres")
    @classmethod
    def _validar_nombres_tutor(cls, v: str) -> str:
        return validate_nombre(v)

    @field_validator("apellido_paterno")
    @classmethod
    def _validar_apellido_paterno_tutor(cls, v: str) -> str:
        return validate_apellido(v, "apellido_paterno")

    @field_validator("apellido_materno")
    @classmethod
    def _validar_apellido_materno_tutor(cls, v: str) -> str:
        return validate_apellido(v, "apellido_materno")

    @field_validator("fuente_empleo")
    @classmethod
    def _fuente_empleo_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_fuente_empleo(v)

    @field_validator("otras_fuentes_ingreso")
    @classmethod
    def _otras_fuentes_ingreso_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_otras_fuentes_ingreso(v)

    @field_validator("nivel_estudios")
    @classmethod
    def _nivel_estudios_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_catalog(v, NIVEL_ESTUDIOS_CATALOG, "nivel_estudios")

    @field_validator("ingreso_mensual")
    @classmethod
    def _ingreso_mensual_valido(cls, v: Optional[int]) -> Optional[int]:
        return validate_ingreso_mensual(v)

    @field_validator("monto_otras_fuentes")
    @classmethod
    def _monto_otras_fuentes_valido(cls, v: Optional[float]) -> Optional[float]:
        return validate_monto_otras_fuentes(v)

    @field_validator("num_hijos")
    @classmethod
    def _num_hijos_valido(cls, v: Optional[int]) -> Optional[int]:
        return validate_num_hijos(v)

    @field_validator("imss_estatus", "infonavit_estatus")
    @classmethod
    def _triestado_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        vv = normalize_text(v)
        return validate_catalog(vv, TRIESTADO_CATALOG, "estatus")

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
    def _antiguedad_anios_valida(cls, v: Optional[int]) -> Optional[int]:
        return validate_antiguedad_anios(v)

    @field_validator("antiguedad_meses_extra")
    @classmethod
    def _antiguedad_meses_valida(cls, v: Optional[int]) -> Optional[int]:
        return validate_antiguedad_meses(v)


class EstudioIn(BaseModel):
    tuvo_silla_previa: bool
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    ciudad_registro: Optional[str] = None
    fecha_estudio: str
    status: str = "borrador"

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: str) -> str:
        return validate_status(v)

    @field_validator("fecha_estudio")
    @classmethod
    def _fecha_estudio_valida(cls, v: str) -> str:
        return validate_fecha_estudio(v)

    @field_validator("como_obtuvo_silla", "ciudad_registro", mode="before")
    @classmethod
    def _normalizar_textos_estudio(cls, v: Optional[str]) -> Optional[str]:
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

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_status(v)

    @model_validator(mode="after")
    def _validar_fecha_estudio_completo(self):
        if self.status == "completo":
            if not self.fecha_estudio:
                raise ValueError("fecha_estudio es obligatorio cuando status es completo")
        return self


class EstudioUpdateResponse(BaseModel):
    estudio_id: int
    status: str
    updated_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/estudios", status_code=201, response_model=EstudioCreateResponse)
def crear_estudio(
    body: EstudioCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin"))],
) -> EstudioCreateResponse:
    """Create a complete estudio socioeconómico with beneficiario, tutores, and study data."""
    _validar_tutores(body.tutores)

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
             (beneficiario_id, usuario_id, tuvo_silla_previa, como_obtuvo_silla,
              elaboro_estudio, fecha_estudio, sede, ciudad_registro, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            beneficiario_id,
            usuario.usuario_id,
            int(estudio.tuvo_silla_previa) if estudio.tuvo_silla_previa is not None else None,
            _resolve_como_obtuvo_silla(estudio.tuvo_silla_previa, estudio.como_obtuvo_silla),
            usuario.nombre,
            estudio.fecha_estudio,
            body.sede,
            body.ciudad_registro,
            estudio.status,
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
        fields["tuvo_silla_previa"] = int(fields["tuvo_silla_previa"])
        fields["como_obtuvo_silla"] = _resolve_como_obtuvo_silla(fields["tuvo_silla_previa"], fields.get("como_obtuvo_silla"))
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

    # --- Validate Tutor 1 required fields ---
    tutor1 = next((t for t in tutores if t.numero_tutor == 1), None)
    if tutor1 is None:
        return  # defensive: no Tutor 1 in list

    # Static required fields (must not be None or empty string)
    missing: list[str] = []
    if tutor1.edad is None:
        missing.append("edad")
    if not tutor1.nivel_estudios:
        missing.append("nivel_estudios")
    if not tutor1.estado_civil:
        missing.append("estado_civil")
    if not tutor1.vivienda:
        missing.append("vivienda")
    if not tutor1.imss_estatus:
        missing.append("imss_estatus")
    if not tutor1.infonavit_estatus:
        missing.append("infonavit_estatus")

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Campos obligatorios de Tutor 1 faltantes: {', '.join(missing)}",
        )

    # Conditional required fields
    missing_cond: list[str] = []

    if not tutor1.sin_empleo:
        if not tutor1.fuente_empleo:
            missing_cond.append("fuente_empleo")
        if tutor1.ingreso_mensual is None:
            missing_cond.append("ingreso_mensual")

        if tutor1.antiguedad_aplica:
            if tutor1.antiguedad_anios is None:
                missing_cond.append("antiguedad_anios")

    if tutor1.otras_fuentes_aplica:
        if not tutor1.otras_fuentes_ingreso:
            missing_cond.append("otras_fuentes_ingreso")
        if tutor1.monto_otras_fuentes is None:
            missing_cond.append("monto_otras_fuentes")

    if missing_cond:
        raise HTTPException(
            status_code=422,
            detail=f"Campos condicionales de Tutor 1 faltantes: {', '.join(missing_cond)}",
        )

    # Tutor 2 obligatoriedad (si existe)
    tutor2 = next((t for t in tutores if t.numero_tutor == 2), None)
    if tutor2:
        static_required_t2 = {
            "edad": tutor2.edad,
            "nivel_estudios": tutor2.nivel_estudios,
            "estado_civil": tutor2.estado_civil,
            "vivienda": tutor2.vivienda,
            "imss_estatus": tutor2.imss_estatus,
            "infonavit_estatus": tutor2.infonavit_estatus,
        }
        missing_t2 = [k for k, v in static_required_t2.items() if v is None or v == ""]
        if missing_t2:
            raise HTTPException(
                status_code=422,
                detail=f"Tutor 2: campos obligatorios faltantes: {', '.join(missing_t2)}"
            )

        conditional_errors_t2 = []

        if not tutor2.sin_empleo:
            if not tutor2.fuente_empleo or not tutor2.fuente_empleo.strip():
                conditional_errors_t2.append("fuente_empleo")
            if tutor2.ingreso_mensual is None:
                conditional_errors_t2.append("ingreso_mensual")

        if not tutor2.sin_empleo and tutor2.antiguedad_aplica:
            if tutor2.antiguedad_anios is None:
                conditional_errors_t2.append("antiguedad_anios")

        if tutor2.otras_fuentes_aplica:
            if not tutor2.otras_fuentes_ingreso or not tutor2.otras_fuentes_ingreso.strip():
                conditional_errors_t2.append("otras_fuentes_ingreso")
            if tutor2.monto_otras_fuentes is None:
                conditional_errors_t2.append("monto_otras_fuentes")

        if conditional_errors_t2:
            raise HTTPException(
                status_code=422,
                detail=f"Tutor 2: campos condicionales obligatorios faltantes: {', '.join(conditional_errors_t2)}"
            )


def _insertar_tutores(db: _DBAdapter, beneficiario_id: int, tutores: list[TutorIn]) -> None:
    for tutor in tutores:
        nombre_compuesto = f"{tutor.nombres} {tutor.apellido_paterno} {tutor.apellido_materno}".strip()
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
                nombre_compuesto,
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
    """Map boolean-like string to DB integer: SI→1, NO→0, None→NULL."""
    if valor is None:
        return None
    mapping: dict[str, Optional[int]] = {"SI": 1, "NO": 0}
    return mapping.get(valor)


def _mapear_de_db(valor: Optional[int]) -> str:
    """Map DB integer to string: 1→SI, 0→NO, NULL→NO."""
    if valor is None:
        return "NO"
    return "SI" if valor == 1 else "NO"


def _calc_antiguedad_meses(tutor: TutorIn) -> Optional[int]:
    if not tutor.antiguedad_aplica:
        return None
    anios = tutor.antiguedad_anios or 0
    meses = tutor.antiguedad_meses_extra or 0
    return (anios * 12) + meses
