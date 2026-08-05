"""
Validators for all form input fields.

All validators are pure functions — they receive raw string values and
either return validated/normalized values or raise ValueError with a
message that includes the field name for structured error reporting.
"""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────
# Constants (single source of truth for regex, catalogs, and limits)
# ──────────────────────────────────────────────────────────────────────────

# Name regex: letters (including Spanish accented and ñ/Ñ), dots, and spaces
_NOMBRE_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ. ]+$")
_NOMBRE_MAX = 60
_APELLIDO_MAX = 40

# Diagnóstico / calle / colonia / fuente empleo / otras fuentes
# "$" is allowed because the same charset validates income descriptions
# ("VENTAS $500") and the frontend DIAGNOSTICO_RE already accepts it.
_DIAGNOSTICO_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\s\-().\/,$]+$")
_DIAGNOSTICO_MAX = 160

_CALLE_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9.\- ]+$")
_CALLE_MAX = 120

_COLONIA_RE = _CALLE_RE
_COLONIA_MAX = 120

_CIUDAD_MAX = 80

_NUM_DOMICILIO_RE = re.compile(r"^[A-Z0-9\-/]+$")
_NUM_DOMICILIO_MAX = 10

_TELEFONO_RE = re.compile(r"^[0-9]{10}$")
_TELEFONO_LEN = 10

# CURP (Clave Única de Registro de Población) — 18 chars, uppercase A-Z/0-9.
# Structure: 4 letters · 6-digit birthdate · sex (H/M) · 2-letter state code
# (incl. NE = nacido en el extranjero) · 3 consonants · homoclave · check digit.
# Frontend mirror must stay identical (see docs/VALIDATION_RULES.md).
_CURP_RE = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])"
    r"[HM](AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|"
    r"PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)"
    r"[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
)
_CURP_LEN = 18
# Dictionary for the check-digit (dígito verificador) algorithm.
_CURP_DICT = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"

# Observaciones / justificación whitelist
_OBS_WHITELIST_RE = re.compile(
    r"^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,:;]*$"
)
_OBS_MAX_LENGTH = 500

_ENTIDAD_WHITELIST_RE = re.compile(
    r"^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,]*$"
)
_ENTIDAD_MAX_LENGTH = 64

# Medidas técnicas
_MEASURE_REGEX = re.compile(r"^[0-9]+(\.[0-9]{1,3})?$")
_MEASURE_INT_DIGITS = 4
_MEASURE_DEC_DIGITS = 3

# ── Catalogs ──
ESTADO_CIVIL_CATALOG = frozenset({
    "SOLTERO", "CASADO", "VIUDO", "DIVORCIADO", "UNION_LIBRE"
})
BOOLEANO_CATALOG = frozenset({"SI", "NO"})
VIVIENDA_CATALOG = frozenset({
    "PROPIA", "RENTADA", "PRESTADA", "FAMILIAR", "INFORMAL", "OTRA"
})
NIVEL_ESTUDIOS_CATALOG = frozenset({
    "NINGUNO", "PRIMARIA", "SECUNDARIA", "BACHILLERATO",
    "LICENCIATURA", "MAESTRIA", "DOCTORADO", "TECNICO"
})
COMO_OBTUVO_SILLA_CATALOG = frozenset({"COMPRA", "DONACION"})

ESTADOS_INEGI = frozenset({
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
    "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
    "31", "32"
})

ESTADOS_INEGI_NOMBRES = {
    "01": "AGUASCALIENTES", "02": "BAJA CALIFORNIA", "03": "BAJA CALIFORNIA SUR",
    "04": "CAMPECHE", "05": "COAHUILA", "06": "COLIMA", "07": "CHIAPAS",
    "08": "CHIHUAHUA", "09": "CIUDAD DE MEXICO", "10": "DURANGO",
    "11": "GUANAJUATO", "12": "GUERRERO", "13": "HIDALGO", "14": "JALISCO",
    "15": "ESTADO DE MEXICO", "16": "MICHOACAN", "17": "MORELOS",
    "18": "NAYARIT", "19": "NUEVO LEON", "20": "OAXACA", "21": "PUEBLA",
    "22": "QUERETARO", "23": "QUINTANA ROO", "24": "SAN LUIS POTOSI",
    "25": "SINALOA", "26": "SONORA", "27": "TABASCO", "28": "TAMAULIPAS",
    "29": "TLAXCALA", "30": "VERACRUZ", "31": "YUCATAN", "32": "ZACATECAS",
}

# Técnica catalogs
ENTORNO_CATALOG = frozenset({
    "Urbano / Interiores", "Rural / Terreno irregular", "Mixto"
})
CONTROL_TRONCO_CATALOG = frozenset({
    "Completo", "Parcial / Requiere apoyo lateral", "Nulo / Requiere soporte total"
})
CONTROL_CABEZA_CATALOG = frozenset({
    "Independiente", "No posee / Requiere cabezal"
})
CONTROL_PIERNAS_CATALOG = frozenset({
    "Parcial", "Nulo"
})
PRIORIDAD_CATALOG = frozenset({"Alta", "Media"})
UNIDAD_MEDIDA_CATALOG = frozenset({"in", "cm"})
UNIDAD_PESO_CATALOG = frozenset({"kg", "lb"})
STATUS_CATALOG = frozenset({"borrador", "completo"})

# Linear measurement columns on solicitudes_tecnicas that are subject to
# cm -> in conversion at finalization time (peso_kg is handled separately
# since its canonical unit is lb, not in).
MEDIDA_TECNICA_COLUMNS = (
    "altura_total_in", "medida_cabeza_asiento", "medida_hombro_asiento",
    "medida_prof_asiento", "medida_rodilla_talon", "medida_ancho_cadera",
)


def convert_medida_to_in(value: Optional[Decimal], unidad: str) -> Optional[Decimal]:
    """Convert a linear measurement to canonical inches.

    Pass-through if value is None or unidad is already "in".
    """
    if value is None:
        return None
    if unidad == "cm":
        return (value / Decimal("2.54")).quantize(Decimal("0.001"))
    return value


def convert_peso_to_lb(value: Optional[Decimal], unidad: str) -> Optional[Decimal]:
    """Convert a weight value to canonical pounds (the canonical storage
    unit for peso_kg despite its column name).

    Pass-through if value is None or unidad is already "lb".
    """
    if value is None:
        return None
    if unidad == "kg":
        return (value * Decimal("2.20462")).quantize(Decimal("0.001"))
    return value


def normalize_medidas_to_canonical(
    values: dict,
    *,
    unidad_medida: str,
    unidad_peso_captura: str,
    measure_cols: tuple = MEDIDA_TECNICA_COLUMNS,
    peso_col: str = "peso_kg",
) -> dict:
    """Convert whichever of measure_cols/peso_col are present in `values` to
    canonical in/lb. Keys not present in the input are not added to the
    output; values are only converted, never added or removed.
    """
    out = dict(values)
    for col in measure_cols:
        if col in out and out[col] is not None:
            out[col] = convert_medida_to_in(Decimal(str(out[col])), unidad_medida)
    if peso_col in out and out[peso_col] is not None:
        out[peso_col] = convert_peso_to_lb(Decimal(str(out[peso_col])), unidad_peso_captura)
    return out
SEXO_CATALOG = frozenset({"M", "F"})

# Monetary limits
INGRESO_MENSUAL_MAX = 999_999_999
MONTO_OTRAS_FUENTES_MAX = 999_999_999

# Integer limits
NUM_HIJOS_MAX = 30
EDAD_MAX = 99
ANTIGUEDAD_ANIOS_MAX = 50
ANTIGUEDAD_MESES_MAX = 11


# ──────────────────────────────────────────────────────────────────────────
# Field labels — single source of truth for column → user-facing label.
# Maps internal DB column / form field names to the visible label the
# capturista sees in the form. Used to avoid leaking technical column names
# (curp_benef, estado_codigo, …) into messages, validations and modals
# (Issue #122). Mirrored by FIELD_LABELS in front/assets/js/validations.js.
# ──────────────────────────────────────────────────────────────────────────

FIELD_LABELS: dict[str, str] = {
    # Beneficiario
    "nombres": "Nombre(s)",
    "apellido_paterno": "Apellido paterno",
    "apellido_materno": "Apellido materno",
    "curp_benef": "CURP",
    "fecha_nacimiento": "Fecha de nacimiento",
    "diagnostico": "Diagnóstico",
    "calle": "Calle",
    "colonia": "Colonia",
    "ciudad": "Ciudad",
    "estado_codigo": "Estado",
    "sexo": "Sexo",
    "telefonos": "Teléfono",
    # Estudio socioeconómico
    "fecha_estudio": "Fecha del estudio",
    "tuvo_silla_previa": "¿Tuvo silla previa?",
    "como_obtuvo_silla": "¿Cómo obtuvo la silla?",
    "elaboro_estudio": "Elaboró el estudio",
    "sede": "Sede",
    "ciudad_registro": "Ciudad de registro",
    "credencial_url": "Credencial",
    "comprobante_domicilio_url": "Comprobante de domicilio",
    # Gestión
    "entidad_solicitante": "Entidad solicitante",
    "prioridad": "Prioridad",
    # Solicitud técnica
    "altura_total_in": "Altura total",
    "peso_kg": "Peso",
    "medida_cabeza_asiento": "Medida cabeza a asiento",
    "medida_hombro_asiento": "Medida hombro a asiento",
    "medida_prof_asiento": "Profundidad de asiento",
    "medida_rodilla_talon": "Medida rodilla a talón",
    "medida_ancho_cadera": "Ancho de cadera",
    "entorno": "Entorno",
    "control_tronco": "Control de tronco",
    "control_cabeza": "Control de cabeza",
    "control_de_piernas": "Control de piernas",
    "foto_url": "Fotografía del paciente",
    # Tutor
    "numero_tutor": "Tutor",
    "edad": "Edad",
    "nivel_estudios": "Nivel de estudios",
    "estado_civil": "Estado civil",
    "vivienda": "Vivienda",
    "imss_estatus": "IMSS",
    "infonavit_estatus": "Infonavit",
    "fuente_empleo": "Fuente de empleo",
    "ingreso_mensual": "Ingreso mensual",
    "antiguedad_anios": "Antigüedad (años)",
    "otras_fuentes_ingreso": "Otras fuentes de ingreso",
    "monto_otras_fuentes": "Monto de otras fuentes",
}


def field_label(field: str) -> str:
    """Resolve a column/field name to its user-facing label.

    Falls back to a humanized version of the field name when the field is
    not in the catalog, so a message is never left showing a raw column.
    """
    if field in FIELD_LABELS:
        return FIELD_LABELS[field]
    return field.replace("_", " ").strip().capitalize()


# ──────────────────────────────────────────────────────────────────────────
# Name validators
# ──────────────────────────────────────────────────────────────────────────

def validate_nombre(value: str) -> str:
    """Validate a nombre field (beneficiario or tutor)."""
    if len(value) < 2 or len(value) > _NOMBRE_MAX:
        raise ValueError(f"nombres debe tener entre 2 y {_NOMBRE_MAX} caracteres")
    if not _NOMBRE_RE.match(value):
        raise ValueError("nombres contiene caracteres no permitidos")
    return value


def validate_apellido(value: str, field_name: str = "apellido") -> str:
    """Validate an apellido field (paterno or materno)."""
    max_len = _APELLIDO_MAX
    if len(value) < 2 or len(value) > max_len:
        raise ValueError(f"{field_name} debe tener entre 2 y {max_len} caracteres")
    if not _NOMBRE_RE.match(value):
        raise ValueError(f"{field_name} contiene caracteres no permitidos")
    return value


# ──────────────────────────────────────────────────────────────────────────
# Text field validators
# ──────────────────────────────────────────────────────────────────────────

def validate_diagnostico(value: str) -> str:
    if len(value) < 3 or len(value) > _DIAGNOSTICO_MAX:
        raise ValueError(f"diagnostico debe tener entre 3 y {_DIAGNOSTICO_MAX} caracteres")
    if not _DIAGNOSTICO_RE.match(value):
        raise ValueError("diagnostico contiene caracteres no permitidos")
    return value


def validate_calle(value: str) -> str:
    if len(value) < 3 or len(value) > _CALLE_MAX:
        raise ValueError(f"calle debe tener entre 3 y {_CALLE_MAX} caracteres")
    if not _CALLE_RE.match(value):
        raise ValueError("calle contiene caracteres no permitidos")
    return value


def validate_colonia(value: str) -> str:
    if len(value) < 2 or len(value) > _COLONIA_MAX:
        raise ValueError(f"colonia debe tener entre 2 y {_COLONIA_MAX} caracteres")
    if not _COLONIA_RE.match(value):
        raise ValueError("colonia contiene caracteres no permitidos")
    return value


def validate_ciudad(value: str) -> str:
    if len(value) < 2 or len(value) > _CIUDAD_MAX:
        raise ValueError(f"ciudad debe tener entre 2 y {_CIUDAD_MAX} caracteres")
    return value


def validate_numero_domicilio(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    # Canonicalize to uppercase: the regex only accepts A-Z and legacy
    # drafts may still carry lowercase values like "12a".
    value = value.strip().upper()
    if not value:
        return None
    if not _NUM_DOMICILIO_RE.match(value):
        raise ValueError("solo se permiten letras, números, guion y diagonal")
    if len(value) > _NUM_DOMICILIO_MAX:
        raise ValueError(f"longitud máxima {_NUM_DOMICILIO_MAX} caracteres")
    return value


def validate_fuente_empleo(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if len(value) > 80:
        raise ValueError("fuente_empleo debe tener máximo 80 caracteres")
    if not _DIAGNOSTICO_RE.match(value):
        raise ValueError("fuente_empleo contiene caracteres no permitidos")
    return value


def validate_otras_fuentes_ingreso(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if len(value) > 100:
        raise ValueError("otras_fuentes_ingreso debe tener máximo 100 caracteres")
    if not _DIAGNOSTICO_RE.match(value):
        raise ValueError("otras_fuentes_ingreso contiene caracteres no permitidos")
    return value


# ──────────────────────────────────────────────────────────────────────────
# Phone & catalog validators
# ──────────────────────────────────────────────────────────────────────────

def validate_telefono(value: str) -> str:
    telefono = re.sub(r"\D", "", value or "")
    if not _TELEFONO_RE.match(telefono):
        raise ValueError("El teléfono debe contener exactamente 10 dígitos numéricos")
    return telefono


def validate_catalog(value: str, catalog: frozenset, field_name: str) -> str:
    if value not in catalog:
        options = ", ".join(sorted(catalog))
        raise ValueError(f"{field_name} fuera de catálogo — debe ser uno de: {options}")
    return value


def validate_sexo(value: str) -> str:
    return validate_catalog(value, SEXO_CATALOG, "sexo")


def validate_estado_codigo(value: str) -> str:
    code = value.strip()
    if code not in ESTADOS_INEGI:
        raise ValueError("estado_codigo fuera de catálogo INEGI")
    return code


def validate_estado_nombre(value: Optional[str], estado_codigo: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if estado_codigo and ESTADOS_INEGI_NOMBRES.get(estado_codigo) != value:
        raise ValueError("estado_nombre no corresponde a estado_codigo")
    return value


def validate_status(value: str) -> str:
    return validate_catalog(value, STATUS_CATALOG, "status")


def validate_unidad_medida(value: str) -> str:
    return validate_catalog(value, UNIDAD_MEDIDA_CATALOG, "unidad_medida")


def validate_unidad_peso(value: str) -> str:
    return validate_catalog(value, UNIDAD_PESO_CATALOG, "unidad_peso_captura")


def validate_prioridad(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return validate_catalog(value, PRIORIDAD_CATALOG, "prioridad")


def validate_entorno(value: str) -> str:
    return validate_catalog(value, ENTORNO_CATALOG, "entorno")


def validate_control_tronco(value: str) -> str:
    return validate_catalog(value, CONTROL_TRONCO_CATALOG, "control_tronco")


def validate_control_cabeza(value: str) -> str:
    return validate_catalog(value, CONTROL_CABEZA_CATALOG, "control_cabeza")


def validate_control_de_piernas(value: str) -> str:
    return validate_catalog(value, CONTROL_PIERNAS_CATALOG, "control_de_piernas")


# ──────────────────────────────────────────────────────────────────────────
# Numeric validators
# ──────────────────────────────────────────────────────────────────────────

def validate_ingreso_mensual(value: Optional[int]) -> Optional[int]:
    if value is not None and (value < 0 or value > INGRESO_MENSUAL_MAX):
        raise ValueError(f"ingreso_mensual fuera de rango — debe estar entre 0 y {INGRESO_MENSUAL_MAX}")
    return value


def validate_monto_otras_fuentes(value: Optional[float]) -> Optional[float]:
    if value is not None and (value < 0 or value > MONTO_OTRAS_FUENTES_MAX):
        raise ValueError(f"monto_otras_fuentes fuera de rango — debe estar entre 0 y {MONTO_OTRAS_FUENTES_MAX}")
    return value


def validate_num_hijos(value: Optional[int]) -> Optional[int]:
    if value is not None and (value < 0 or value > NUM_HIJOS_MAX):
        raise ValueError(f"num_hijos debe estar entre 0 y {NUM_HIJOS_MAX}")
    return value


def validate_edad(value: Optional[int]) -> Optional[int]:
    if value is not None and (value < 0 or value > EDAD_MAX):
        raise ValueError(f"edad debe estar entre 0 y {EDAD_MAX}")
    return value


def validate_antiguedad_anios(value: Optional[int]) -> Optional[int]:
    if value is not None and (value < 0 or value > ANTIGUEDAD_ANIOS_MAX):
        raise ValueError(f"antiguedad_anios debe estar entre 0 y {ANTIGUEDAD_ANIOS_MAX}")
    return value


def validate_antiguedad_meses(value: Optional[int]) -> Optional[int]:
    if value is not None and (value < 0 or value > ANTIGUEDAD_MESES_MAX):
        raise ValueError(f"antiguedad_meses_extra debe estar entre 0 y {ANTIGUEDAD_MESES_MAX}")
    return value





def validate_edad_tutor(value: Optional[int]) -> Optional[int]:
    if value is not None and (value < 18 or value > EDAD_MAX):
        raise ValueError(f"edad del tutor debe estar entre 18 y {EDAD_MAX}")
    return value


def validate_numero_tutor(value: int) -> int:
    if value not in (1, 2):
        raise ValueError("numero_tutor debe ser 1 o 2")
    return value


# ──────────────────────────────────────────────────────────────────────────
# Date validators
# ──────────────────────────────────────────────────────────────────────────

def validate_fecha_nacimiento(value: str) -> str:
    """Validate ISO date format YYYY-MM-DD."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        raise ValueError("fecha_nacimiento debe tener formato YYYY-MM-DD")
    return value


def validate_fecha_estudio(value: str) -> str:
    """Validate ISO date format YYYY-MM-DD."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        raise ValueError("fecha_estudio debe tener formato YYYY-MM-DD")
    return value


def _curp_digito_verificador(curp: str) -> str:
    """Compute the official CURP check digit from its first 17 characters."""
    suma = sum(_CURP_DICT.index(ch) * (18 - i) for i, ch in enumerate(curp[:17]))
    return str((10 - (suma % 10)) % 10)


def validate_curp_formato(value: str) -> str:
    """Validate and normalize a CURP by FORMAT ONLY (length + structure).

    Does NOT verify the check digit (dígito verificador). Use for the **admin**
    path: an administrator may need to register a real CURP whose check digit
    does not match the standard algorithm (documented RENAPO issuance anomalies).
    Returns the uppercased, trimmed CURP. Raises ValueError on a format failure.
    The DB CHECK constraint (`chk_beneficiarios_curp_formato`) enforces this same
    regex, so anything that passes here also passes at the database layer.
    """
    if value is None:
        raise ValueError("curp es obligatoria")
    curp = value.strip().upper()
    if len(curp) != _CURP_LEN:
        raise ValueError(f"curp debe tener exactamente {_CURP_LEN} caracteres")
    if not _CURP_RE.match(curp):
        raise ValueError("curp tiene un formato inválido")
    return curp


def validate_curp(value: str) -> str:
    """Validate and normalize a Mexican CURP (format + check digit).

    Returns the uppercased, trimmed CURP. Raises ValueError on any failure.
    """
    curp = validate_curp_formato(value)
    if _curp_digito_verificador(curp) != curp[17]:
        raise ValueError("curp inválida: el dígito verificador no coincide")
    return curp


# ──────────────────────────────────────────────────────────────────────────
# Observaciones / entidad / justificación (existing validators preserved)
# ──────────────────────────────────────────────────────────────────────────

def validate_padecimiento(value: str) -> str:
    if len(value) > _OBS_MAX_LENGTH:
        raise ValueError(
            f"padecimiento: máximo {_OBS_MAX_LENGTH} caracteres permitidos"
        )
    if not _OBS_WHITELIST_RE.match(value):
        raise ValueError(
            "padecimiento: contiene caracteres no permitidos"
        )
    return value


def validate_entidad_solicitante(value: str) -> str:
    if len(value) > _ENTIDAD_MAX_LENGTH:
        raise ValueError(
            f"entidad_solicitante: máximo {_ENTIDAD_MAX_LENGTH} caracteres permitidos"
        )
    if not _ENTIDAD_WHITELIST_RE.match(value):
        raise ValueError(
            "entidad_solicitante: contiene caracteres no permitidos"
        )
    return value


def validate_justificacion(value: str) -> str:
    if len(value) > _OBS_MAX_LENGTH:
        raise ValueError(
            f"justificacion: máximo {_OBS_MAX_LENGTH} caracteres permitidos"
        )
    if not _OBS_WHITELIST_RE.match(value):
        raise ValueError(
            "justificacion: contiene caracteres no permitidos"
        )
    return value


# ──────────────────────────────────────────────────────────────────────────
# Medida técnica (existing validator preserved)
# ──────────────────────────────────────────────────────────────────────────

def validate_medida_tecnica(value: str, field_name: str) -> Decimal:
    if not _MEASURE_REGEX.match(value):
        raise ValueError(f"{field_name}: formato inválido — solo dígitos y un punto decimal")

    if "." in value:
        int_part, dec_part = value.split(".", 1)
    else:
        int_part, dec_part = value, ""

    stripped_int = int_part.lstrip("0") or "0"
    if len(stripped_int) > _MEASURE_INT_DIGITS:
        raise ValueError(f"{field_name}: máximo {_MEASURE_INT_DIGITS} dígitos enteros permitidos")

    try:
        d = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"{field_name}: formato inválido")

    normalized = d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return normalized


# ──────────────────────────────────────────────────────────────────────────
# Auth validators
# ──────────────────────────────────────────────────────────────────────────

def validate_email_format(value: str) -> str:
    """Minimal email validation (RFC 5322 subset)."""
    email = value.lower().strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("email debe ser una dirección válida")
    if len(email) > 254:
        raise ValueError("email excede 254 caracteres")
    return email


def validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("password debe tener al menos 8 caracteres")
    if len(value) > 128:
        raise ValueError("password excede 128 caracteres")
    return value


def validate_nombre_usuario(value: str) -> str:
    """Validate user creation nombre (min 2, max 100)."""
    v = value.strip()
    if len(v) < 2:
        raise ValueError("nombre debe tener al menos 2 caracteres")
    if len(v) > 100:
        raise ValueError("nombre excede 100 caracteres")
    return v


# ──────────────────────────────────────────────────────────────────────────
# Draft-mode wrapper — skips validation for None / empty-string
# ──────────────────────────────────────────────────────────────────────────

def validate_optional(validator):
    """
    Wrap a validator to skip validation when value is None or empty string.

    In draft mode (borrador), all fields are optional. This wrapper makes
    any validator a no-op for None/"" so that Pydantic field_validator
    methods can reuse existing validators without enforcing completeness.

    Usage:
        @field_validator("nombres")
        @classmethod
        def _validar_nombres(cls, v: Optional[str]) -> Optional[str]:
            return validate_optional(validate_nombre)(v)
    """
    def wrapper(value):
        if value is None or value == "":
            return value
        return validator(value)
    return wrapper
