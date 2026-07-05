"""Contract tests for Phase 3 technical workbench frontend."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TECNICA_FILE = ROOT / "front" / "Tecnico-view" / "vista_tecnicos.html"
ADMIN_USERS_FILE = ROOT / "front" / "Admin-view" / "admin-usuarios.html"
REGION_FILE = ROOT / "front" / "Capturista-view" / "seleccion-region.html"
VALIDATIONS_FILE = ROOT / "front" / "assets" / "js" / "validations.js"
SOCIOECONOMICO_FILE = ROOT / "front" / "Capturista-view" / "socioeconomico.html"
CAPTURISTA_TECNICA_FILE = ROOT / "front" / "Capturista-view" / "tecnica.html"
GESTION_FILE = ROOT / "front" / "Capturista-view" / "gestion.html"
ADMIN_BENEFICIARIOS_FILE = ROOT / "front" / "admin-beneficiarios.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_tecnica_declares_workbench_list_filters_and_states() -> None:
    html = _read(TECNICA_FILE)

    assert "id=\"input-search\"" in html
    assert "id=\"filter-pais\"" in html
    assert "id=\"filter-region\"" in html
    assert "id=\"filter-ciudad\"" in html
    assert "id=\"filter-sede\"" in html
    assert "id=\"filter-foto\"" in html
    assert "id=\"state-loading\"" in html
    assert "id=\"state-empty\"" in html
    assert "id=\"list-container\"" in html
    assert "id=\"pagination\"" in html


def test_tecnica_uses_phase2_operational_endpoints() -> None:
    html = _read(TECNICA_FILE)

    assert "return ApiClient.fetch(path, opts);" in html
    assert '"/paises"' in html
    assert '"/regiones?pais_id=" + paisId' in html
    assert '"/tecnica/beneficiarios/export?" + params.toString()' in html
    assert '"/tecnica/beneficiarios?" + params.toString()' in html
    assert '"/tecnica/beneficiarios/" + beneficiarioId' in html


def test_tecnica_renders_readonly_snapshot_and_participants() -> None:
    html = _read(TECNICA_FILE)

    assert "function renderDetail(data)" in html
    assert "id=\"modal-overlay\"" in html
    assert "id=\"modal-content\"" in html
    assert "Tutores / Referencias" in html
    assert "modal-tabs" in html
    assert '{ id: "ident", label: "Identificación"' in html
    assert '{ id: "clin",  label: "Datos clínicos"' in html
    assert '{ id: "obs",   label: "Observaciones"' in html
    assert '{ id: "files", label: "Archivos"' in html
    assert "Vista de solo lectura" in html
    assert "modalFooter.classList.add(\"hidden\");" in html


def test_admin_users_does_not_declare_stale_pending_reviews_widget() -> None:
    html = _read(ADMIN_USERS_FILE)

    assert "id=\"form-crear\"" in html
    assert "id=\"tabla-usuarios\"" in html
    assert "return ApiClient.fetch(path, opts);" in html
    assert "id=\"tecnica-revisiones-card\"" not in html
    assert "revisiones-pendientes" not in html


def test_admin_users_normal_flow_does_not_expose_permanent_delete() -> None:
    html = _read(ADMIN_USERS_FILE)

    assert "hardDeleteUsuario" not in html
    assert "permanent=true" not in html
    assert "delete_forever" not in html
    assert "Eliminar permanentemente" not in html
    assert "Desactivar usuario y conservar sus registros" in html


def test_region_flow_routes_tecnico_to_workbench_without_beneficiario_dependency() -> None:
    html = _read(REGION_FILE)

    assert "if (session.rol === 'tecnico')" in html
    assert "window.location.href = '../Tecnico-view/vista_tecnicos.html';" in html
    assert "localStorage.removeItem('beneficiario_id');" in html


def test_frontend_uppercase_normalization_is_explicit_opt_in() -> None:
    validations = _read(VALIDATIONS_FILE)
    socio = _read(SOCIOECONOMICO_FILE)
    tecnica = _read(CAPTURISTA_TECNICA_FILE)
    gestion = _read(GESTION_FILE)
    admin_beneficiarios = _read(ADMIN_BENEFICIARIOS_FILE)

    assert 'data-uppercase="true"' in socio
    assert 'dataset?.uppercase === "true"' in validations
    assert "data-no-uppercase" not in validations
    assert "UPPERCASE_EXCLUDED_NAME_RE" not in validations

    assert 'name="curp"\n                type="text"\n                data-uppercase="true"' in socio
    assert 'name="tutor1_nombres"\n                      type="text"\n                      data-uppercase="true"' in socio
    assert 'name="tutor2_fuente_empleo"\n                    type="text"\n                    data-uppercase="true"' in socio
    assert 'name="entidad_solicitante"\n                placeholder="Nombre de la institución o particular"\n                type="text"\n                data-uppercase="true"' in gestion
    assert '_field("nombres", "Nombres", "text", { maxlength: 60, required: true, "data-uppercase": "true" })' in admin_beneficiarios

    assert 'name="diagnostico"\n                type="text"\n                data-uppercase="true"' not in tecnica
    assert 'id="padecimiento-otra-texto"\n                    data-uppercase="true"' not in tecnica
    assert 'name="justificacion"\n                placeholder="Información adicional relevante sobre la necesidad de esta silla específica..."\n                rows="3"\n                data-uppercase="true"' not in gestion
