"""
Validators for técnica form input fields.

All validators are pure functions — they receive raw string values and
either return validated/normalized values or raise ValueError with a
message that includes the field name for structured error reporting.
"""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# ---------------------------------------------------------------------------
# observaciones_posturales — whitelist validator
# ---------------------------------------------------------------------------

# Allowed characters: letters (a-z, A-Z, including Spanish accented and ñ/Ñ,
# German umlauts), digits 0-9, spaces, and punctuation: () / - . , : ;
_OBS_WHITELIST_RE = re.compile(
    r"^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,:;]*$"
)

_OBS_MAX_LENGTH = 500


def validate_observaciones_posturales(value: str) -> str:
    """Validate and return the observaciones_posturales string.

    Rules:
    - Only characters in the whitelist regex are allowed
    - Maximum 500 characters

    Returns the value unchanged on success.
    Raises ValueError with field name on failure.
    """
    if len(value) > _OBS_MAX_LENGTH:
        raise ValueError(
            f"observaciones_posturales: máximo {_OBS_MAX_LENGTH} caracteres permitidos"
        )

    if not _OBS_WHITELIST_RE.match(value):
        raise ValueError(
            "observaciones_posturales: contiene caracteres no permitidos"
        )

    return value


# ---------------------------------------------------------------------------
# medida técnica — digit+dots validator → Decimal normalizer
# ---------------------------------------------------------------------------

# Regex: one or more digits, optionally followed by a single dot and 1-3 digits.
# Leading zeros are allowed in the regex (handled during normalization).
_MEASURE_REGEX = re.compile(r"^[0-9]+(\.[0-9]{1,3})?$")


def validate_medida_tecnica(value: str, field_name: str) -> Decimal:
    """Validate a measurement string and return a normalized Decimal.

    Rules:
    - Only digits and at most one decimal point are allowed
    - Maximum 4 integer digits (after stripping leading zeros for the check)
    - Maximum 3 decimal digits
    - Normalized to ####.### (e.g., "2" → Decimal("2.000"), "002.3" → Decimal("2.300"))

    Returns a Decimal with exactly 3 decimal places.
    Raises ValueError with the field name on failure.
    """
    if not _MEASURE_REGEX.match(value):
        raise ValueError(f"{field_name}: formato inválido — solo dígitos y un punto decimal")

    # Split integer and decimal parts
    if "." in value:
        int_part, dec_part = value.split(".", 1)
    else:
        int_part, dec_part = value, ""

    # Check integer digit count (after stripping leading zeros to get actual magnitude)
    stripped_int = int_part.lstrip("0") or "0"
    if len(stripped_int) > 4:
        raise ValueError(f"{field_name}: máximo 4 dígitos enteros permitidos")

    # decimal part already checked by regex (max 3 digits)

    # Convert to Decimal and normalize to 3 decimal places
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"{field_name}: formato inválido")

    # Quantize to exactly 3 decimal places
    normalized = d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    return normalized
