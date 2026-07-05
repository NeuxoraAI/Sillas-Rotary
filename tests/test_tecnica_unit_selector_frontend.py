"""Contract tests for tecnica.html unit selector restore."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TECNICA_FILE = ROOT / "front" / "Capturista-view" / "tecnica.html"


def _read_tecnica_html() -> str:
    return TECNICA_FILE.read_text(encoding="utf-8")


def test_declares_unit_to_selector_mapping() -> None:
    html = _read_tecnica_html()

    assert "function toMeasurementSystem(unit)" in html
    assert 'unit === "metric" || unit === "cm"' in html
    assert 'unit === "imperial" || unit === "in"' in html


def test_restores_selector_from_backend_or_local_draft_unit_field() -> None:
    html = _read_tecnica_html()

    assert "function restoreMeasurementSystem(data, setVal)" in html
    assert "data?.unidad_captura || data?.unidad_medida" in html
    assert 'setVal("unidad_medida", system)' in html
    assert html.count("restoreMeasurementSystem(data, setVal);") >= 2
