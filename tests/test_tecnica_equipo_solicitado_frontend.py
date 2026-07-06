"""Contract tests for equipo_solicitado in the capturista technical form."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TECNICA_FILE = ROOT / "front" / "Capturista-view" / "tecnica.html"


def _read_tecnica_html() -> str:
    return TECNICA_FILE.read_text(encoding="utf-8")


def test_declares_equipo_solicitado_field() -> None:
    html = _read_tecnica_html()

    assert 'name="equipo_solicitado"' in html


def test_collects_equipo_solicitado_into_tecnica_data_and_submit_payload() -> None:
    html = _read_tecnica_html()

    assert 'equipo_solicitado: get("equipo_solicitado") || null' in html
    assert 'equipo_solicitado: tecnicaData.equipo_solicitado || null' in html


def test_includes_equipo_solicitado_in_draft_save_payload() -> None:
    html = _read_tecnica_html()

    draft_save_section = html[html.index("async function guardarBorradorDesdeTecnica") :]
    draft_save_section = draft_save_section[: draft_save_section.index('ApiClient.fetch("/guardar-borrador"')]

    assert "const tecnicaData = getTecnicaFormData();" in draft_save_section
    assert "const payload = {" in draft_save_section
    assert 'equipo_solicitado: tecnicaData.equipo_solicitado || null' in draft_save_section


def test_restores_equipo_solicitado_from_backend_and_local_draft() -> None:
    html = _read_tecnica_html()

    assert html.count('setVal("equipo_solicitado", data.equipo_solicitado);') >= 2
