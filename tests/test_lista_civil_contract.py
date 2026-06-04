from pathlib import Path
import sys
import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-secret-" + ("x" * 32))

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))
from routers.socioeconomico import ESTADO_CIVIL_CATALOG, TutorIn  # noqa: E402


FRONT_FILE = Path(__file__).resolve().parents[1] / "front" / "Capturista-view" / "socioeconomico.html"


_KNOWN_CATALOG = {"SOLTERO", "CASADO", "VIUDO", "DIVORCIADO", "UNION_LIBRE"}


def test_estado_civil_catalog_constant_is_closed() -> None:
    assert ESTADO_CIVIL_CATALOG == _KNOWN_CATALOG


@pytest.mark.parametrize("value", ["SOLTERO", "CASADO", "VIUDO", "DIVORCIADO", "UNION_LIBRE", None, ""])
def test_tutorin_accepts_catalog_and_normalizes_empty(value: str | None) -> None:
    tutor = TutorIn(numero_tutor=1, nombres="Tutor", apellido_paterno="Test", apellido_materno="Muestra", estado_civil=value)
    if value == "":
        assert tutor.estado_civil is None
    else:
        assert tutor.estado_civil == value


def test_tutorin_rejects_estado_civil_outside_catalog() -> None:
    with pytest.raises(ValidationError) as exc:
        TutorIn(numero_tutor=1, nombres="Tutor", apellido_paterno="Test", apellido_materno="Muestra", estado_civil="Union libre")

    error_text = str(exc.value)
    assert "CASADO" in error_text
    assert "SOLTERO" in error_text
    assert "VIUDO" in error_text
    assert "DIVORCIADO" in error_text
    assert "UNION_LIBRE" in error_text


def test_front_uses_select_for_tutor_estado_civil() -> None:
    content = FRONT_FILE.read_text(encoding="utf-8")

    assert 'name="tutor1_estado_civil"' in content
    assert 'name="tutor2_estado_civil"' in content
    assert 'name="tutor1_estado_civil" type="text"' not in content
    assert 'name="tutor2_estado_civil" type="text"' not in content


def test_front_estado_civil_select_has_fixed_catalog_options() -> None:
    content = FRONT_FILE.read_text(encoding="utf-8")

    assert '<option value="">Selecciona una opción</option>' in content
    assert '<option value="CASADO">Casado / Casada</option>' in content
    assert '<option value="SOLTERO">Soltero / Soltera</option>' in content
    assert '<option value="VIUDO">Viudo / Viuda</option>' in content
    assert '<option value="DIVORCIADO">Divorciado / Divorciada</option>' in content
    assert '<option value="UNION_LIBRE">Unión libre</option>' in content


def test_front_prefill_uses_legacy_fallback_for_unknown_estado_civil() -> None:
    content = FRONT_FILE.read_text(encoding="utf-8")

    assert "setEstadoCivilCatalogValue" in content
    assert "ESTADO_CIVIL_CATALOG.includes(val)" in content
    assert "setEstadoCivilCatalogValue(`tutor${num}_estado_civil`, t.estado_civil);" in content


def test_front_getformdata_keeps_estado_civil_payload_shape() -> None:
    content = FRONT_FILE.read_text(encoding="utf-8")

    assert "estado_civil: get('tutor1_estado_civil')," in content
    assert "estado_civil: get('tutor2_estado_civil')," in content


def test_front_patch_payload_reuses_getformdata_and_includes_tutores() -> None:
    content = FRONT_FILE.read_text(encoding="utf-8")

    assert "const payload = getFormData(status);" in content
    assert "...payload.estudio," in content
    assert "tutores: payload.tutores," in content
