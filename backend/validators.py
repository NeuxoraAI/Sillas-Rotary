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
_DIAGNOSTICO_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\s\-().\/,]+$")
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
TRIESTADO_CATALOG = frozenset({"SI", "NO"})
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
    "Independiente", "Intermitente", "No posee / Requiere cabezal"
})
PRIORIDAD_CATALOG = frozenset({"Alta", "Media"})
UNIDAD_MEDIDA_CATALOG = frozenset({"in", "cm"})
STATUS_CATALOG = frozenset({"borrador", "completo"})
SEXO_CATALOG = frozenset({"M", "F", "NE"})

# Monetary limits
INGRESO_MENSUAL_MAX = 9_999_999
MONTO_OTRAS_FUENTES_MAX = 999_999

# Integer limits
NUM_HIJOS_MAX = 30
EDAD_MAX = 99
ANTIGUEDAD_ANIOS_MAX = 50
ANTIGUEDAD_MESES_MAX = 11


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


# ──────────────────────────────────────────────────────────────────────────
# Observaciones / entidad / justificación (existing validators preserved)
# ──────────────────────────────────────────────────────────────────────────

def validate_observaciones_posturales(value: str) -> str:
    if len(value) > _OBS_MAX_LENGTH:
        raise ValueError(
            f"observaciones_posturales: máximo {_OBS_MAX_LENGTH} caracteres permitidos"
        )
    if not _OBS_WHITELIST_RE.match(value):
        raise ValueError(
            "observaciones_posturales: contiene caracteres no permitidos"
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
