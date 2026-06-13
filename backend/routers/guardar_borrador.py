"""
Master Draft Save router — borrador-maestro.

Provides:
  POST /api/guardar-borrador — atomic create or update of all 3 forms
  GET  /api/borrador/{estudio_id} — retrieve a complete draft for resumption
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, assert_resource_owner, require_roles
from routers.regiones import generate_folio
from routers.socioeconomico import _resolve_document_refs
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
    validate_fecha_nacimiento,
    validate_fecha_estudio,
    validate_email_format,
    validate_catalog,
    validate_ingreso_mensual,
    validate_monto_otras_fuentes,
    validate_num_hijos,
    validate_edad_tutor,
    validate_antiguedad_anios,
    validate_antiguedad_meses,
    validate_fuente_empleo,
    validate_otras_fuentes_ingreso,
    validate_status,
    validate_entorno,
    validate_control_tronco,
    validate_control_cabeza,
    validate_control_de_piernas,
    validate_observaciones_posturales,
    validate_unidad_medida,
    validate_unidad_peso,
    validate_prioridad,
    validate_entidad_solicitante,
    validate_justificacion,
    validate_optional,
    ESTADO_CIVIL_CATALOG,
    TRIESTADO_CATALOG,
    VIVIENDA_CATALOG,
    NIVEL_ESTUDIOS_CATALOG,
    COMO_OBTUVO_SILLA_CATALOG,
    SEXO_CATALOG,
)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────
# Pydantic model — every field Optional for draft mode
# ──────────────────────────────────────────────────────────────────────────

class GuardarBorradorRequest(BaseModel):
    """Master draft payload covering all 3 forms (beneficiario + estudio + solicitud)."""

    # ── IDs for UPDATE mode ──
    estudio_id: Optional[int] = None
    solicitud_id: Optional[int] = None
    beneficiario_id: Optional[int] = None

    # ── Region context ──
    region_id: Optional[int] = None
    sede: Optional[str] = None

    # ── Beneficiario ──
    nombres: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    diagnostico: Optional[str] = None
    calle: Optional[str] = None
    num_ext: Optional[str] = None
    num_int: Optional[str] = None
    colonia: Optional[str] = None
    ciudad: Optional[str] = None
    estado_codigo: Optional[str] = None
    estado_nombre: Optional[str] = None
    sexo: Optional[str] = None
    telefonos: Optional[str] = None
    email: Optional[str] = None

    # ── Estudio ──
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    voluntario_contacto: Optional[str] = None
    ciudad_registro: Optional[str] = None
    fecha_estudio: Optional[str] = None
    credencial_path: Optional[str] = None
    credencial_url: Optional[str] = None
    comprobante_domicilio_path: Optional[str] = None
    comprobante_domicilio_url: Optional[str] = None
    status: Optional[str] = "borrador"

    # ── Solicitud (técnica) ──
    entorno: Optional[str] = None
    control_tronco: Optional[str] = None
    control_cabeza: Optional[str] = None
    control_de_piernas: Optional[str] = None
    observaciones_posturales: Optional[str] = None
    unidad_medida: Optional[str] = None
    altura_total_in: Optional[str] = None
    peso_kg: Optional[str] = None
    unidad_peso_captura: Optional[str] = None
    medida_cabeza_asiento: Optional[str] = None
    medida_hombro_asiento: Optional[str] = None
    medida_prof_asiento: Optional[str] = None
    medida_rodilla_talon: Optional[str] = None
    medida_ancho_cadera: Optional[str] = None
    foto_path: Optional[str] = None
    foto_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None

    # ── Tutor 1 ──
    tutor1_nombres: Optional[str] = None
    tutor1_apellido_paterno: Optional[str] = None
    tutor1_apellido_materno: Optional[str] = None
    tutor1_email: Optional[str] = None
    tutor1_edad: Optional[int] = None
    tutor1_nivel_estudios: Optional[str] = None
    tutor1_estado_civil: Optional[str] = None
    tutor1_num_hijos: Optional[int] = None
    tutor1_vivienda: Optional[str] = None
    tutor1_fuente_empleo: Optional[str] = None
    tutor1_antiguedad_aplica: Optional[bool] = None
    tutor1_antiguedad_anios: Optional[int] = None
    tutor1_antiguedad_meses_extra: Optional[int] = None
    tutor1_ingreso_mensual: Optional[int] = None
    tutor1_sin_empleo: Optional[bool] = None
    tutor1_otras_fuentes_aplica: Optional[bool] = None
    tutor1_otras_fuentes_ingreso: Optional[str] = None
    tutor1_monto_otras_fuentes: Optional[float] = None
    tutor1_imss_estatus: Optional[str] = None
    tutor1_infonavit_estatus: Optional[str] = None

    # ── Tutor 2 ──
    tutor2_nombres: Optional[str] = None
    tutor2_apellido_paterno: Optional[str] = None
    tutor2_apellido_materno: Optional[str] = None
    tutor2_email: Optional[str] = None
    tutor2_edad: Optional[int] = None
    tutor2_nivel_estudios: Optional[str] = None
    tutor2_estado_civil: Optional[str] = None
    tutor2_num_hijos: Optional[int] = None
    tutor2_vivienda: Optional[str] = None
    tutor2_fuente_empleo: Optional[str] = None
    tutor2_antiguedad_aplica: Optional[bool] = None
    tutor2_antiguedad_anios: Optional[int] = None
    tutor2_antiguedad_meses_extra: Optional[int] = None
    tutor2_ingreso_mensual: Optional[int] = None
    tutor2_sin_empleo: Optional[bool] = None
    tutor2_otras_fuentes_aplica: Optional[bool] = None
    tutor2_otras_fuentes_ingreso: Optional[str] = None
    tutor2_monto_otras_fuentes: Optional[float] = None
    tutor2_imss_estatus: Optional[str] = None
    tutor2_infonavit_estatus: Optional[str] = None

    # ── Normalization (mode="before"): uppercase + collapse whitespace,
    #    mirrors BeneficiarioIn so drafts store the same canonical format ──

    @field_validator("nombres", "tutor1_nombres", "tutor2_nombres",
                     "apellido_paterno", "apellido_materno",
                     "tutor1_apellido_paterno", "tutor1_apellido_materno",
                     "tutor2_apellido_paterno", "tutor2_apellido_materno",
                     "diagnostico", "calle", "colonia", "ciudad",
                     "elaboro_estudio", "voluntario_contacto",
                     "tutor1_fuente_empleo", "tutor2_fuente_empleo",
                     "tutor1_otras_fuentes_ingreso", "tutor2_otras_fuentes_ingreso",
                     "observaciones_posturales", "justificacion",
                     "entidad_solicitante", mode="before")
    @classmethod
    def _normalizar_textos_libres(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return normalize_text(v)

    # ── Format-only validation (skip None / "") ──

    @field_validator("nombres", "tutor1_nombres", "tutor2_nombres")
    @classmethod
    def _validar_nombres(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_nombre)(v)

    @field_validator("apellido_paterno", "apellido_materno",
                     "tutor1_apellido_paterno", "tutor1_apellido_materno",
                     "tutor2_apellido_paterno", "tutor2_apellido_materno")
    @classmethod
    def _validar_apellidos(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(lambda x: validate_apellido(x, "apellido"))(v)

    @field_validator("fecha_nacimiento")
    @classmethod
    def _fecha_nacimiento_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_fecha_nacimiento)(v)

    @field_validator("diagnostico")
    @classmethod
    def _diagnostico_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_diagnostico)(v)

    @field_validator("calle")
    @classmethod
    def _calle_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_calle)(v)

    @field_validator("colonia")
    @classmethod
    def _colonia_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_colonia)(v)

    @field_validator("ciudad")
    @classmethod
    def _ciudad_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_ciudad)(v)

    @field_validator("num_ext", "num_int")
    @classmethod
    def _numero_domicilio_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_numero_domicilio)(v)

    @field_validator("telefonos")
    @classmethod
    def _telefonos_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_telefono)(v)

    @field_validator("estado_codigo")
    @classmethod
    def _estado_codigo_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_estado_codigo)(v)

    @field_validator("sexo")
    @classmethod
    def _sexo_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_sexo)(v)

    @field_validator("estado_nombre")
    @classmethod
    def _estado_nombre_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_estado_nombre(v, None)

    @field_validator("email", "tutor1_email", "tutor2_email")
    @classmethod
    def _email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_email_format(v)

    @field_validator("fecha_estudio")
    @classmethod
    def _fecha_estudio_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_fecha_estudio)(v)

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_status)(v)

    # ── Catalog validators ──

    @field_validator("tutor1_nivel_estudios", "tutor2_nivel_estudios", mode="before")
    @classmethod
    def _nivel_estudios_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        vv = normalize_text(v)
        return validate_catalog(vv, NIVEL_ESTUDIOS_CATALOG, "nivel_estudios")

    @field_validator("tutor1_estado_civil", "tutor2_estado_civil", mode="before")
    @classmethod
    def _estado_civil_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        vv = normalize_text(v)
        return validate_catalog(vv, ESTADO_CIVIL_CATALOG, "estado_civil")

    @field_validator("tutor1_vivienda", "tutor2_vivienda", mode="before")
    @classmethod
    def _vivienda_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        vv = normalize_text(v)
        return validate_catalog(vv, VIVIENDA_CATALOG, "vivienda")

    @field_validator("como_obtuvo_silla", mode="before")
    @classmethod
    def _como_obtuvo_silla_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        vv = normalize_text(v)
        return validate_catalog(vv, COMO_OBTUVO_SILLA_CATALOG, "como_obtuvo_silla")

    # ── Numeric validators (already None-safe) ──

    @field_validator("tutor1_edad", "tutor2_edad")
    @classmethod
    def _edad_tutor_valida(cls, v: Optional[int]) -> Optional[int]:
        return validate_edad_tutor(v)

    @field_validator("tutor1_ingreso_mensual", "tutor2_ingreso_mensual")
    @classmethod
    def _ingreso_mensual_valido(cls, v: Optional[int]) -> Optional[int]:
        return validate_ingreso_mensual(v)

    @field_validator("tutor1_monto_otras_fuentes", "tutor2_monto_otras_fuentes")
    @classmethod
    def _monto_otras_fuentes_valido(cls, v: Optional[float]) -> Optional[float]:
        return validate_monto_otras_fuentes(v)

    @field_validator("tutor1_num_hijos", "tutor2_num_hijos")
    @classmethod
    def _num_hijos_valido(cls, v: Optional[int]) -> Optional[int]:
        return validate_num_hijos(v)

    @field_validator("tutor1_antiguedad_anios", "tutor2_antiguedad_anios")
    @classmethod
    def _antiguedad_anios_valida(cls, v: Optional[int]) -> Optional[int]:
        return validate_antiguedad_anios(v)

    @field_validator("tutor1_antiguedad_meses_extra", "tutor2_antiguedad_meses_extra")
    @classmethod
    def _antiguedad_meses_valida(cls, v: Optional[int]) -> Optional[int]:
        return validate_antiguedad_meses(v)

    @field_validator("tutor1_fuente_empleo", "tutor2_fuente_empleo")
    @classmethod
    def _fuente_empleo_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_fuente_empleo(v)

    @field_validator("tutor1_otras_fuentes_ingreso", "tutor2_otras_fuentes_ingreso")
    @classmethod
    def _otras_fuentes_ingreso_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_otras_fuentes_ingreso(v)

    # ── Técnica catalog validators ──

    @field_validator("entorno")
    @classmethod
    def _entorno_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_entorno)(v)

    @field_validator("control_tronco")
    @classmethod
    def _control_tronco_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_control_tronco)(v)

    @field_validator("control_cabeza")
    @classmethod
    def _control_cabeza_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_control_cabeza)(v)

    @field_validator("control_de_piernas")
    @classmethod
    def _control_de_piernas_valido(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_control_de_piernas)(v)

    @field_validator("observaciones_posturales")
    @classmethod
    def _obs_posturales_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_observaciones_posturales(v)

    @field_validator("unidad_medida")
    @classmethod
    def _unidad_medida_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_unidad_medida)(v)

    @field_validator("unidad_peso_captura")
    @classmethod
    def _unidad_peso_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_unidad_peso)(v)

    @field_validator("prioridad")
    @classmethod
    def _prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional(validate_prioridad)(v)

    @field_validator("entidad_solicitante")
    @classmethod
    def _entidad_solicitante_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_entidad_solicitante(v)

    @field_validator("justificacion")
    @classmethod
    def _justificacion_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_justificacion(v)


class GuardarBorradorResponse(BaseModel):
    estudio_id: int
    solicitud_id: int
    beneficiario_id: int
    folio: str
    status: str


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _compose_nombre(body: GuardarBorradorRequest) -> str:
    """Compose canonical nombre from structured name fields."""
    parts = [
        body.nombres or "",
        body.apellido_paterno or "",
        body.apellido_materno or "",
    ]
    return " ".join(p for p in parts if p).strip()


def _tutor_has_data(body: GuardarBorradorRequest, numero: int) -> bool:
    """Check whether any tutor fields were provided for tutor N (1 or 2)."""
    prefix = f"tutor{numero}_"
    fields = [
        "nombres", "apellido_paterno", "apellido_materno", "email", "edad",
        "nivel_estudios", "estado_civil", "num_hijos", "vivienda",
        "fuente_empleo", "ingreso_mensual", "otras_fuentes_ingreso",
        "monto_otras_fuentes",
    ]
    for field in fields:
        val = getattr(body, prefix + field, None)
        if val is not None and val != "" and val != 0:
            return True
    return False


def _build_tutor_params(body: GuardarBorradorRequest, numero: int, beneficiario_id: int) -> tuple:
    """Build INSERT params tuple for a tutor row."""
    prefix = f"tutor{numero}_"
    g = lambda f: getattr(body, prefix + f, None)
    nombres = g("nombres") or ""
    ap_pat = g("apellido_paterno") or ""
    ap_mat = g("apellido_materno") or ""
    nombre_compuesto = " ".join(p for p in [nombres, ap_pat, ap_mat] if p).strip()

    anios = g("antiguedad_anios") or 0
    meses = g("antiguedad_meses_extra") or 0
    antiguedad_meses = (anios * 12) + meses if g("antiguedad_aplica") else None

    return (
        beneficiario_id,
        numero,
        nombre_compuesto or None,
        g("email"),
        g("edad"),
        g("nivel_estudios"),
        g("estado_civil"),
        g("num_hijos") if g("num_hijos") is not None else 0,
        g("vivienda"),
        None if g("sin_empleo") else (g("fuente_empleo")),
        None,
        0 if g("sin_empleo") else (g("ingreso_mensual") or 0),
        1 if g("imss_estatus") == "SI" else 0 if g("imss_estatus") == "NO" else None,
        1 if g("infonavit_estatus") == "SI" else 0 if g("infonavit_estatus") == "NO" else None,
        antiguedad_meses,
        int(bool(g("antiguedad_aplica"))) if g("antiguedad_aplica") is not None else 0,
        int(bool(g("sin_empleo"))) if g("sin_empleo") is not None else 0,
        int(bool(g("otras_fuentes_aplica"))) if g("otras_fuentes_aplica") is not None else 0,
        g("otras_fuentes_ingreso") if g("otras_fuentes_aplica") else None,
        g("monto_otras_fuentes") if g("otras_fuentes_aplica") else None,
    )


def _mapear_de_db(valor: Optional[int]) -> Optional[str]:
    """Map DB integer to string: 1→SI, 0→NO, NULL→None."""
    if valor is None:
        return None
    return "SI" if valor == 1 else "NO"


def _tutor_response(t: dict) -> dict:
    """Transform a DB tutor row into API response format."""
    t["imss_estatus"] = _mapear_de_db(t.pop("tiene_imss", None))
    t["infonavit_estatus"] = _mapear_de_db(t.pop("tiene_infonavit", None))
    if t.get("ingreso_mensual") is not None:
        t["ingreso_mensual"] = int(t["ingreso_mensual"])
    return t


# ──────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────

@router.post("/guardar-borrador", status_code=201, response_model=GuardarBorradorResponse)
def guardar_borrador(
    body: GuardarBorradorRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin", "organizacion"))],
) -> GuardarBorradorResponse:
    """
    Atomic draft save: create or update all 3 forms in one transaction.

    CREATE mode (no estudio_id):
      - Generates folio, inserts beneficiario + estudio + solicitud atomically.

    UPDATE mode (has estudio_id):
      - Updates existing beneficiario + estudio + solicitud atomically.
    """
    if body.estudio_id is not None:
        return _update_borrador(body, db, usuario)
    else:
        return _create_borrador(body, db, usuario)


def _create_borrador(
    body: GuardarBorradorRequest,
    db: _DBAdapter,
    usuario: CurrentUser,
) -> GuardarBorradorResponse:
    """CREATE mode: insert beneficiario + estudio + solicitud in a transaction."""
    if body.region_id is None:
        raise HTTPException(status_code=422, detail="region_id es obligatorio para crear un borrador")

    # Generate folio
    try:
        folio = generate_folio(db, body.region_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="No se pudo generar el folio")

    nombre_composed = _compose_nombre(body) or None

    try:
        db.execute("BEGIN")

        # 1. INSERT beneficiario
        beneficiario_id = db.execute(
            """
            INSERT INTO beneficiarios
                (nombre, nombres, apellido_paterno, apellido_materno,
                 fecha_nacimiento, diagnostico, calle, num_ext, num_int, colonia, ciudad,
                 estado_codigo, estado_nombre, sexo, telefonos, email,
                 folio, region_id, sede)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                nombre_composed,
                body.nombres,
                body.apellido_paterno,
                body.apellido_materno,
                body.fecha_nacimiento,
                body.diagnostico,
                body.calle,
                body.num_ext,
                body.num_int,
                body.colonia,
                body.ciudad,
                body.estado_codigo,
                body.estado_nombre,
                body.sexo,
                body.telefonos,
                body.email,
                folio,
                body.region_id,
                body.sede,
            ),
        ).fetchone()["id"]

        # 2. INSERT tutores (if any data)
        for num in (1, 2):
            if _tutor_has_data(body, num):
                params = _build_tutor_params(body, num, beneficiario_id)
                db.execute(
                    """
                    INSERT INTO tutores
                        (beneficiario_id, numero_tutor, nombre, email, edad, nivel_estudios,
                         estado_civil, num_hijos, vivienda, fuente_empleo, antiguedad,
                         ingreso_mensual, tiene_imss, tiene_infonavit,
                         antiguedad_meses, antiguedad_aplica, sin_empleo,
                         otras_fuentes_aplica, otras_fuentes_ingreso, monto_otras_fuentes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params,
                )

        # 3. INSERT estudio
        credencial_path, credencial_url = _resolve_document_refs(
            document_path=body.credencial_path,
            document_url=body.credencial_url,
        )
        comprobante_path, comprobante_url = _resolve_document_refs(
            document_path=body.comprobante_domicilio_path,
            document_url=body.comprobante_domicilio_url,
        )
        estudio_id = db.execute(
            """
            INSERT INTO estudios_socioeconomicos
                (beneficiario_id, usuario_id, tuvo_silla_previa, como_obtuvo_silla,
                 elaboro_estudio, fecha_estudio, sede, ciudad_registro,
                 credencial_path, credencial_url,
                 comprobante_domicilio_path, comprobante_domicilio_url, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                beneficiario_id,
                usuario.usuario_id,
                int(body.tuvo_silla_previa) if body.tuvo_silla_previa is not None else None,
                body.como_obtuvo_silla,
                body.elaboro_estudio or usuario.nombre,
                body.fecha_estudio,
                body.sede,
                body.ciudad_registro,
                credencial_path,
                credencial_url,
                comprobante_path,
                comprobante_url,
                body.status or "borrador",
            ),
        ).fetchone()["id"]

        # 3b. Register the volunteer capture for organizacion accounts
        #     (mirrors POST /estudios behavior; only on first insert so
        #     draft updates don't double-count)
        if usuario.rol == "organizacion" and body.elaboro_estudio:
            from routers.socioeconomico import _upsert_voluntario
            _upsert_voluntario(
                db, usuario.usuario_id, body.elaboro_estudio, body.voluntario_contacto
            )

        # 4. INSERT solicitud
        solicitud_id = db.execute(
            """
            INSERT INTO solicitudes_tecnicas
                (beneficiario_id, usuario_id, entorno, control_tronco, control_cabeza,
                 control_de_piernas, observaciones_posturales, altura_total_in, peso_kg,
                 medida_cabeza_asiento, medida_hombro_asiento, medida_prof_asiento,
                 medida_rodilla_talon, medida_ancho_cadera, unidad_captura,
                 unidad_peso_captura, foto_url, entidad_solicitante, prioridad,
                 justificacion, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                beneficiario_id,
                usuario.usuario_id,
                body.entorno,
                body.control_tronco,
                body.control_cabeza,
                body.control_de_piernas,
                body.observaciones_posturales,
                _parse_decimal_or_none(body.altura_total_in),
                _parse_decimal_or_none(body.peso_kg),
                _parse_decimal_or_none(body.medida_cabeza_asiento),
                _parse_decimal_or_none(body.medida_hombro_asiento),
                _parse_decimal_or_none(body.medida_prof_asiento),
                _parse_decimal_or_none(body.medida_rodilla_talon),
                _parse_decimal_or_none(body.medida_ancho_cadera),
                body.unidad_medida,
                body.unidad_peso_captura,
                body.foto_url,
                body.entidad_solicitante,
                body.prioridad,
                body.justificacion,
                body.status or "borrador",
            ),
        ).fetchone()["id"]

        db.commit()
    except HTTPException:
        db.execute("ROLLBACK")
        raise
    except Exception as exc:
        db.execute("ROLLBACK")
        raise HTTPException(status_code=500, detail="Error interno al guardar el borrador") from exc

    return GuardarBorradorResponse(
        estudio_id=estudio_id,
        solicitud_id=solicitud_id,
        beneficiario_id=beneficiario_id,
        folio=folio,
        status=body.status or "borrador",
    )


def _update_borrador(
    body: GuardarBorradorRequest,
    db: _DBAdapter,
    usuario: CurrentUser,
) -> GuardarBorradorResponse:
    """UPDATE mode: patch beneficiario + estudio + solicitud atomically."""
    # Verify estudio exists and check ownership
    existing = db.execute(
        "SELECT id, usuario_id, beneficiario_id FROM estudios_socioeconomicos WHERE id = %s",
        (body.estudio_id,),
    ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    assert_resource_owner(existing["usuario_id"], usuario, db=db, estudio_id=body.estudio_id)

    beneficiario_id = existing["beneficiario_id"]

    # Find solicitud by beneficiario_id (or by solicitud_id if provided)
    solicitud_existing = None
    if body.solicitud_id is not None:
        solicitud_existing = db.execute(
            "SELECT id FROM solicitudes_tecnicas WHERE id = %s",
            (body.solicitud_id,),
        ).fetchone()
    if solicitud_existing is None:
        solicitud_existing = db.execute(
            "SELECT id FROM solicitudes_tecnicas WHERE beneficiario_id = %s ORDER BY id DESC LIMIT 1",
            (beneficiario_id,),
        ).fetchone()

    solicitud_id = solicitud_existing["id"] if solicitud_existing else None

    try:
        db.execute("BEGIN")

        # 1. UPDATE beneficiario (only non-None fields)
        _patch_beneficiario(db, body, beneficiario_id)

        # 2. UPDATE tutores (delete + re-insert if tutor data present)
        for num in (1, 2):
            if _tutor_has_data(body, num):
                db.execute(
                    "DELETE FROM tutores WHERE beneficiario_id = %s AND numero_tutor = %s",
                    (beneficiario_id, num),
                )
                params = _build_tutor_params(body, num, beneficiario_id)
                db.execute(
                    """
                    INSERT INTO tutores
                        (beneficiario_id, numero_tutor, nombre, email, edad, nivel_estudios,
                         estado_civil, num_hijos, vivienda, fuente_empleo, antiguedad,
                         ingreso_mensual, tiene_imss, tiene_infonavit,
                         antiguedad_meses, antiguedad_aplica, sin_empleo,
                         otras_fuentes_aplica, otras_fuentes_ingreso, monto_otras_fuentes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params,
                )

        # 3. UPDATE estudio (only non-None fields)
        _patch_estudio(db, body, body.estudio_id)

        # 4. UPDATE solicitud (only non-None fields, if solicitud exists)
        if solicitud_id is not None:
            _patch_solicitud(db, body, solicitud_id)

        db.commit()
    except HTTPException:
        db.execute("ROLLBACK")
        raise
    except Exception as exc:
        db.execute("ROLLBACK")
        raise HTTPException(status_code=500, detail="Error interno al actualizar el borrador") from exc

    # Fetch current folio
    ben_row = db.execute(
        "SELECT folio FROM beneficiarios WHERE id = %s", (beneficiario_id,)
    ).fetchone()
    folio = ben_row["folio"] if ben_row else ""

    return GuardarBorradorResponse(
        estudio_id=body.estudio_id,
        solicitud_id=solicitud_id or 0,
        beneficiario_id=beneficiario_id,
        folio=folio,
        status="borrador",
    )


def _patch_beneficiario(db: _DBAdapter, body: GuardarBorradorRequest, ben_id: int) -> None:
    """Build and execute a partial UPDATE for beneficiario."""
    fields: dict[str, any] = {}
    ben_mappings = [
        ("nombres", body.nombres),
        ("apellido_paterno", body.apellido_paterno),
        ("apellido_materno", body.apellido_materno),
        ("fecha_nacimiento", body.fecha_nacimiento),
        ("diagnostico", body.diagnostico),
        ("calle", body.calle),
        ("num_ext", body.num_ext),
        ("num_int", body.num_int),
        ("colonia", body.colonia),
        ("ciudad", body.ciudad),
        ("estado_codigo", body.estado_codigo),
        ("estado_nombre", body.estado_nombre),
        ("sexo", body.sexo),
        ("telefonos", body.telefonos),
        ("email", body.email),
    ]
    for db_col, val in ben_mappings:
        if val is not None:
            fields[db_col] = val

    # Update composed nombre if any name part changed
    if body.nombres is not None or body.apellido_paterno is not None or body.apellido_materno is not None:
        existing = db.execute(
            "SELECT nombres, apellido_paterno, apellido_materno FROM beneficiarios WHERE id = %s",
            (ben_id,),
        ).fetchone()
        if existing:
            nombres = body.nombres if body.nombres is not None else existing["nombres"] or ""
            ap_pat = body.apellido_paterno if body.apellido_paterno is not None else existing["apellido_paterno"] or ""
            ap_mat = body.apellido_materno if body.apellido_materno is not None else existing["apellido_materno"] or ""
            fields["nombre"] = " ".join(p for p in [nombres, ap_pat, ap_mat] if p).strip() or None

    if not fields:
        return

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [ben_id]
    db.execute(f"UPDATE beneficiarios SET {set_clause} WHERE id = %s", tuple(values))


def _patch_estudio(db: _DBAdapter, body: GuardarBorradorRequest, estudio_id: int) -> None:
    """Build and execute a partial UPDATE for estudio."""
    fields: dict[str, any] = {}
    if body.tuvo_silla_previa is not None:
        fields["tuvo_silla_previa"] = int(body.tuvo_silla_previa)
    if body.como_obtuvo_silla is not None:
        fields["como_obtuvo_silla"] = body.como_obtuvo_silla
    if body.elaboro_estudio is not None:
        fields["elaboro_estudio"] = body.elaboro_estudio
    if body.ciudad_registro is not None:
        fields["ciudad_registro"] = body.ciudad_registro
    if body.fecha_estudio is not None:
        fields["fecha_estudio"] = body.fecha_estudio
    if body.sede is not None:
        fields["sede"] = body.sede
    if body.credencial_path is not None or body.credencial_url is not None:
        credencial_path, credencial_url = _resolve_document_refs(
            document_path=body.credencial_path,
            document_url=body.credencial_url,
        )
        if credencial_path is not None:
            fields["credencial_path"] = credencial_path
            fields["credencial_url"] = credencial_url
    if body.comprobante_domicilio_path is not None or body.comprobante_domicilio_url is not None:
        comprobante_path, comprobante_url = _resolve_document_refs(
            document_path=body.comprobante_domicilio_path,
            document_url=body.comprobante_domicilio_url,
        )
        if comprobante_path is not None:
            fields["comprobante_domicilio_path"] = comprobante_path
            fields["comprobante_domicilio_url"] = comprobante_url
    if body.status is not None:
        fields["status"] = body.status

    if not fields:
        return

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [estudio_id]
    db.execute(
        f"UPDATE estudios_socioeconomicos SET {set_clause}, updated_at = NOW() WHERE id = %s",
        tuple(values),
    )


def _patch_solicitud(db: _DBAdapter, body: GuardarBorradorRequest, solicitud_id: int) -> None:
    """Build and execute a partial UPDATE for solicitud."""
    fields: dict[str, any] = {}
    sol_mappings = [
        ("entorno", body.entorno),
        ("control_tronco", body.control_tronco),
        ("control_cabeza", body.control_cabeza),
        ("control_de_piernas", body.control_de_piernas),
        ("observaciones_posturales", body.observaciones_posturales),
        ("entidad_solicitante", body.entidad_solicitante),
        ("prioridad", body.prioridad),
        ("justificacion", body.justificacion),
        ("status", body.status),
    ]
    for db_col, val in sol_mappings:
        if val is not None:
            fields[db_col] = val

    if body.unidad_medida is not None:
        fields["unidad_captura"] = body.unidad_medida
    if body.unidad_peso_captura is not None:
        fields["unidad_peso_captura"] = body.unidad_peso_captura
    if body.foto_url is not None:
        fields["foto_url"] = body.foto_url

    # Medida fields — parse strings to Decimal or None
    medida_mappings = [
        ("altura_total_in", body.altura_total_in),
        ("peso_kg", body.peso_kg),
        ("medida_cabeza_asiento", body.medida_cabeza_asiento),
        ("medida_hombro_asiento", body.medida_hombro_asiento),
        ("medida_prof_asiento", body.medida_prof_asiento),
        ("medida_rodilla_talon", body.medida_rodilla_talon),
        ("medida_ancho_cadera", body.medida_ancho_cadera),
    ]
    for db_col, val in medida_mappings:
        if val is not None:
            fields[db_col] = _parse_decimal_or_none(val)

    if not fields:
        return

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [solicitud_id]
    db.execute(
        f"UPDATE solicitudes_tecnicas SET {set_clause}, updated_at = NOW() WHERE id = %s",
        tuple(values),
    )


def _parse_decimal_or_none(value: Optional[str]) -> Optional[object]:
    """Parse a string to Decimal, or return None for empty/null."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    from decimal import Decimal
    try:
        return Decimal(str(value))
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────
# GET /api/borrador/{estudio_id}
# ──────────────────────────────────────────────────────────────────────────

@router.get("/borrador/{estudio_id}")
def obtener_borrador(
    estudio_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin", "organizacion"))],
) -> dict:
    """
    Retrieve a complete draft (all 3 forms) for resumption.

    Only the owner capturista or an admin may access. Returns 404 if the
    estudio is not found or its status is not "borrador".
    """
    estudio_row = db.execute(
        "SELECT * FROM estudios_socioeconomicos WHERE id = %s", (estudio_id,)
    ).fetchone()

    if estudio_row is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    if estudio_row["status"] != "borrador":
        raise HTTPException(status_code=404, detail="Este estudio ya no está en estado borrador")

    assert_resource_owner(estudio_row["usuario_id"], usuario, db=db, estudio_id=estudio_id)

    beneficiario_row = db.execute(
        "SELECT * FROM beneficiarios WHERE id = %s",
        (estudio_row["beneficiario_id"],),
    ).fetchone()

    tutores_rows = db.execute(
        "SELECT * FROM tutores WHERE beneficiario_id = %s ORDER BY numero_tutor",
        (estudio_row["beneficiario_id"],),
    ).fetchall()

    solicitud_row = db.execute(
        "SELECT * FROM solicitudes_tecnicas WHERE beneficiario_id = %s ORDER BY id DESC LIMIT 1",
        (estudio_row["beneficiario_id"],),
    ).fetchone()

    def _row_to_json(row: dict) -> dict:
        """Convert datetime objects to ISO strings for JSON serialization."""
        if not row:
            return row
        result = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result

    response = _row_to_json(dict(estudio_row))
    response["beneficiario"] = _row_to_json(dict(beneficiario_row)) if beneficiario_row else None
    response["tutores"] = [_row_to_json(_tutor_response(dict(t))) for t in tutores_rows] if tutores_rows else []
    response["solicitud"] = _row_to_json(dict(solicitud_row)) if solicitud_row else None

    return response
