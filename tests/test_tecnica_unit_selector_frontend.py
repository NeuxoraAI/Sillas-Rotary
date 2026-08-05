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
    assert "restoreMeasurementSystem(data, setVal);" in html


def test_restore_dispatches_change_so_unit_labels_resync() -> None:
    """Regression guard: setVal only assigns .value, so restoring the unit
    system asynchronously (after DraftStore.hydrateIfNeeded()) must dispatch
    a "change" event or the field-level unit labels installed by
    setupUnidadMedidaLabels() never re-run and stay stuck on the default.
    """
    html = _read_tecnica_html()

    set_val_call = html.index('setVal("unidad_medida", system)')
    dispatch_call = html.index(
        'document.getElementById("unidad_medida")?.dispatchEvent(new Event("change"));'
    )
    assert dispatch_call > set_val_call
