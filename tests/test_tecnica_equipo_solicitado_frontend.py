"""Contract tests for Equipo Solicitado persistence in tecnica.html."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TECNICA_FILE = ROOT / "front" / "Capturista-view" / "tecnica.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_equipo_solicitado_is_collected_sent_and_restored() -> None:
    html = _read(TECNICA_FILE)

    assert 'name="equipo_solicitado"' in html
    assert 'equipo_solicitado: get("equipo_solicitado")' in html
    assert 'equipo_solicitado: get("equipo_solicitado") || null' in html
    assert 'equipo_solicitado: tecnicaData.equipo_solicitado || null' in html
    assert 'setVal("equipo_solicitado", data.equipo_solicitado)' in html
