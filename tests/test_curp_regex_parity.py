"""Guarda la paridad de la validación de CURP entre backend y frontend.

El regex y el diccionario del dígito verificador viven DUPLICADOS en Python
(`backend/validators.py`) y en JavaScript (`front/assets/js/validations.js`).
Deben mantenerse idénticos (Issue #32); este test falla si divergen, para no
depender de una nota de mantenimiento manual.
"""

from pathlib import Path
import re
import sys
import os

os.environ.setdefault("JWT_SECRET", "test-secret-" + ("x" * 32))

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))
from validators import (  # noqa: E402
    _CURP_RE,
    _CURP_DICT,
    validate_curp,
    validate_curp_formato,
    _curp_digito_verificador,
)

_JS_FILE = Path(__file__).resolve().parents[1] / "front" / "assets" / "js" / "validations.js"


def _js_source() -> str:
    return _JS_FILE.read_text(encoding="utf-8")


def test_curp_regex_identical_frontend_backend() -> None:
    """El patrón `_CURP_RE` (Python) y `CURP_RE` (JS) deben ser byte-idénticos."""
    m = re.search(r"const CURP_RE = /(?P<pat>.*?)/;", _js_source())
    assert m, "No se encontró `const CURP_RE = /.../;` en validations.js"
    assert m.group("pat") == _CURP_RE.pattern, (
        "El regex de CURP divergió entre validations.js y validators.py — "
        "deben mantenerse idénticos (Issue #32)."
    )


def test_curp_dict_identical_frontend_backend() -> None:
    """El diccionario del dígito verificador debe ser idéntico en ambos lados."""
    m = re.search(r'const CURP_DICT = "(?P<dict>[^"]*)";', _js_source())
    assert m, "No se encontró `const CURP_DICT = \"...\";` en validations.js"
    assert m.group("dict") == _CURP_DICT


def test_validate_curp_accepts_valid_and_rejects_bad_check_digit() -> None:
    """El dígito verificador es determinista: el correcto pasa, cualquier otro falla."""
    base17 = "PEGJ850315HDFRRL0"
    dv = _curp_digito_verificador(base17 + "0")  # solo usa los primeros 17
    valida = base17 + dv
    assert validate_curp(valida) == valida  # dígito correcto → OK

    mal = base17 + str((int(dv) + 1) % 10)  # cualquier otro dígito
    try:
        validate_curp(mal)
    except ValueError as e:
        assert "dígito verificador" in str(e)
    else:  # pragma: no cover
        raise AssertionError("una CURP con dígito verificador incorrecto debía fallar")


def test_validate_curp_rejects_bad_format_and_length() -> None:
    import pytest

    with pytest.raises(ValueError, match="18 caracteres"):
        validate_curp("PEGJ90")
    with pytest.raises(ValueError, match="formato inválido"):
        validate_curp("0000000000000000AA")  # 18 chars pero no matchea el regex


def test_admin_format_only_accepts_valid_format_with_bad_check_digit() -> None:
    """El path admin (`validate_curp_formato`) acepta una CURP real atípica:
    formato válido aunque el dígito verificador NO coincida (anomalía RENAPO).
    """
    base17 = "PEGJ850315HDFRRL0"
    bad_dv = str((int(_curp_digito_verificador(base17 + "0")) + 1) % 10)
    curp_atipica = base17 + bad_dv

    # El validador estricto la rechaza…
    import pytest

    with pytest.raises(ValueError, match="dígito verificador"):
        validate_curp(curp_atipica)

    # …pero el de solo-formato (admin) la acepta y la normaliza.
    assert validate_curp_formato(curp_atipica) == curp_atipica
    # Y normaliza a mayúsculas / trim.
    assert validate_curp_formato("  " + curp_atipica.lower() + " ") == curp_atipica


def test_admin_format_only_still_rejects_malformed() -> None:
    """Solo-formato NO es 'sin validación': una CURP malformada sigue fallando
    (coincide con el CHECK de la BD, evitando errores 500 por constraint)."""
    import pytest

    with pytest.raises(ValueError, match="18 caracteres"):
        validate_curp_formato("PEGJ90")
    with pytest.raises(ValueError, match="formato inválido"):
        validate_curp_formato("0000000000000000AA")
