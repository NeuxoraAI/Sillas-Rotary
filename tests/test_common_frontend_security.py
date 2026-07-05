"""Contract tests for shared frontend HTML escaping."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "front"
COMMON_JS = FRONT / "assets" / "js" / "common.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_common_escape_covers_attribute_delimiters() -> None:
    js = _read(COMMON_JS)

    assert "function _esc(value)" in js
    assert '.replace(/&/g, "&amp;")' in js
    assert '.replace(/</g, "&lt;")' in js
    assert '.replace(/>/g, "&gt;")' in js
    assert '.replace(/"/g, "&quot;")' in js
    assert '.replace(/\'/g, "&#039;")' in js
    assert "window._escapeHtml = _esc;" in js


def test_common_helpers_loaded_on_escape_consumers() -> None:
    expected_scripts = {
        FRONT / "login.html": 'src="assets/js/common.js"',
        FRONT / "perfil-organizacion.html": 'src="assets/js/common.js"',
        FRONT / "admin-beneficiarios.html": 'src="assets/js/common.js"',
        FRONT / "Capturista-view" / "perfil-capturista.html": 'src="../assets/js/common.js"',
        FRONT / "Capturista-view" / "seleccion-region.html": 'src="../assets/js/common.js"',
        FRONT / "Admin-view" / "admin-usuarios.html": 'src="../assets/js/common.js"',
        FRONT / "Admin-view" / "admin-regiones.html": 'src="../assets/js/common.js"',
        FRONT / "Tecnico-view" / "vista_tecnicos.html": 'src="../assets/js/common.js"',
    }

    for path, script in expected_scripts.items():
        assert script in _read(path), path


def test_no_local_escape_helpers_or_inline_heatmap_handlers_remain() -> None:
    html = "\n".join(path.read_text(encoding="utf-8") for path in FRONT.rglob("*.html"))

    assert "function _esc" not in html
    assert "function _escapeHtml" not in html
    assert "onmouseenter=" not in html
    assert "onmouseleave=" not in html
    assert 'data-tooltip="${_esc(' in html
