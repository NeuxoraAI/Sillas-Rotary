"""Contract tests for Phase 3 technical workbench frontend."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TECNICA_FILE = ROOT / "front" / "tecnica.html"
ADMIN_USERS_FILE = ROOT / "front" / "admin-usuarios.html"
REGION_FILE = ROOT / "front" / "seleccion-region.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_tecnica_declares_workbench_list_filters_and_states() -> None:
    html = _read(TECNICA_FILE)

    assert "id=\"search-q\"" in html
    assert "id=\"filter-sede\"" in html
    assert "id=\"filter-estado\"" in html
    assert "id=\"filter-revision\"" in html
    assert "id=\"tabla-beneficiarios\"" in html
    assert "id=\"empty-state\"" in html


def test_tecnica_uses_phase2_operational_endpoints() -> None:
    html = _read(TECNICA_FILE)

    assert "fetch('/api/tecnica/beneficiarios'" in html
    assert "`/api/tecnica/beneficiarios/${beneficiarioId}`" in html
    assert "`/api/tecnica/beneficiarios/${beneficiarioId}/iniciar`" in html
    assert "`/api/tecnica/procesos/${procesoId}/continuar`" in html
    assert "`/api/tecnica/procesos/${procesoId}/finalizar`" in html
    assert "`/api/tecnica/procesos/${procesoId}/solicitar-revision`" in html
    assert "`/api/tecnica/procesos/${procesoId}/pdf`" in html


def test_tecnica_renders_readonly_snapshot_and_participants() -> None:
    html = _read(TECNICA_FILE)

    assert "renderReadonlySnapshot" in html
    assert "readonly_base" in html
    assert "id=\"detalle-readonly\"" in html
    assert "id=\"participantes-log\"" in html
    assert "id=\"btn-iniciar\"" in html
    assert "id=\"btn-continuar\"" in html
    assert "id=\"btn-finalizar\"" in html
    assert "id=\"btn-revision\"" in html
    assert "id=\"btn-pdf\"" in html


def test_admin_users_declares_pending_reviews_widget() -> None:
    html = _read(ADMIN_USERS_FILE)

    assert "id=\"tecnica-revisiones-card\"" in html
    assert "id=\"count-revisiones\"" in html
    assert "id=\"tabla-revisiones\"" in html
    assert "fetch('/api/admin/tecnica/revisiones-pendientes'" in html


def test_region_flow_routes_tecnico_to_workbench_without_beneficiario_dependency() -> None:
    html = _read(REGION_FILE)

    assert "if (session.rol === 'tecnico')" in html
    assert "window.location.href = 'tecnica.html';" in html
    assert "localStorage.removeItem('beneficiario_id');" in html
