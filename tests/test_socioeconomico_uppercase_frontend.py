"""Contract tests for socioeconomic uppercase normalization."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOCIOECONOMICO_FILE = ROOT / "front" / "Capturista-view" / "socioeconomico.html"


def _read_socioeconomico_html() -> str:
    return SOCIOECONOMICO_FILE.read_text(encoding="utf-8")


def test_declares_uppercase_normalization_helpers() -> None:
    html = _read_socioeconomico_html()

    assert "function normalizeUpperText(value)" in html
    assert "function shouldUppercaseSocioField(name)" in html
    assert "function setupUppercaseSocioFields()" in html


def test_serializes_socioeconomic_alphabetic_fields_uppercase() -> None:
    html = _read_socioeconomico_html()

    assert "const getUpper = (name) => normalizeUpperText(get(name));" in html
    assert 'nombres: getUpper("nombres")' in html
    assert 'apellido_paterno: getUpper("apellido_paterno")' in html
    assert 'calle: getUpper("calle")' in html
    assert 'colonia: getUpper("colonia")' in html
    assert 'nombres: getUpper("tutor1_nombres")' in html
    assert 'fuente_empleo: getUpper("tutor1_fuente_empleo")' in html
    assert 'otras_fuentes_ingreso: getUpper("tutor2_otras_fuentes_ingreso")' in html


def test_rehydrates_and_autosaves_uppercase_values() -> None:
    html = _read_socioeconomico_html()

    assert "values[field.name] = shouldUppercaseSocioField(field.name)" in html
    assert "first.value = shouldUppercaseSocioField(name)" in html
    assert "setupUppercaseSocioFields();" in html
