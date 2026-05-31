"""
Integration tests for admin beneficiario management endpoints.

Tests cover:
- List, export, detail endpoints
- PATCH beneficiario, estudio, solicitud, gestion
- DELETE cascade
- Authorization (403 for non-admin)
- 404 for non-existent beneficiario
"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def beneficiario_fixture(client, admin_headers, capturista_user, region_lon, pais_mx):
    """Create a sample beneficiario with estudio via capturista, return the snapshot."""
    # Login as capturista
    cap_token_res = client.post("/api/auth/login", json={
        "email": "cap@test.mx", "password": "cappass123",
    })
    cap_headers = {"Authorization": f"Bearer {cap_token_res.json()['access_token']}"}

    payload = {
        "region_id": region_lon["id"],
        "sede": "León sede Forum",
        "ciudad_registro": "LEON, GTO",
        "beneficiario": {
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "ADMIN",
            "apellido_materno": "TEST",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "num_ext": "12A",
            "num_int": "3",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "estado_nombre": "GUANAJUATO",
            "sexo": "M",
            "telefonos": "4621234567",
        },
        "tutores": [
            {
                "numero_tutor": 1,
                "nombres": "TUTOR",
                "apellido_paterno": "ADMIN",
                "apellido_materno": "TEST",
                "email": "tutor@test.mx",
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "imss_estatus": "SI",
                "infonavit_estatus": "NO",
            }
        ],
        "estudio": {
            "tuvo_silla_previa": False,
            "elaboro_estudio": "Capturista Test",
            "fecha_estudio": "2026-04-18",
            "status": "completo",
        },
    }
    res = client.post("/api/estudios", json=payload, headers=cap_headers)
    assert res.status_code == 201, f"beneficiario_fixture failed: {res.text}"
    estudio_data = res.json()
    beneficiario_id = estudio_data["beneficiario_id"]

    # Get full detail via admin
    detail_res = client.get(
        f"/api/admin/beneficiarios/{beneficiario_id}",
        headers=admin_headers,
    )
    assert detail_res.status_code == 200
    return detail_res.json()


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------

class TestAdminBeneficiarioAuth:
    """Authorization: only admin can access these endpoints."""

    def test_non_admin_list_returns_403(self, client, capturista_headers):
        """Capturista cannot list beneficiarios via admin endpoint."""
        res = client.get("/api/admin/beneficiarios", headers=capturista_headers)
        assert res.status_code == 403

    def test_non_admin_detail_returns_403(self, client, capturista_headers, beneficiario_fixture):
        """Capturista cannot access admin detail endpoint."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.get(f"/api/admin/beneficiarios/{ben_id}", headers=capturista_headers)
        assert res.status_code == 403

    def test_non_admin_patch_returns_403(self, client, capturista_headers, beneficiario_fixture):
        """Capturista cannot PATCH via admin endpoint."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.patch(
            f"/api/admin/beneficiarios/{ben_id}",
            json={"nombres": "INTRUSO"},
            headers=capturista_headers,
        )
        assert res.status_code == 403

    def test_non_admin_delete_returns_403(self, client, capturista_headers, beneficiario_fixture):
        """Capturista cannot DELETE via admin endpoint."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.delete(f"/api/admin/beneficiarios/{ben_id}", headers=capturista_headers)
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# List + Export tests
# ---------------------------------------------------------------------------

class TestAdminList:
    """GET /api/admin/beneficiarios — list with filters."""

    def test_list_returns_items(self, client, admin_headers, beneficiario_fixture):
        """Admin list returns beneficiarios with pagination."""
        res = client.get("/api/admin/beneficiarios", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_search_by_name(self, client, admin_headers, beneficiario_fixture):
        """Search filter works."""
        res = client.get("/api/admin/beneficiarios?q=ADMIN", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        items = data["items"]
        assert any("ADMIN" in (i.get("nombre", "") or "").upper() for i in items)

    def test_export_returns_xlsx(self, client, admin_headers, beneficiario_fixture):
        """Export returns Excel file."""
        res = client.get("/api/admin/beneficiarios/export", headers=admin_headers)
        assert res.status_code == 200
        content_type = res.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "excel" in content_type


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class TestAdminDetail:
    """GET /api/admin/beneficiarios/{id} — full detail snapshot."""

    def test_detail_returns_snapshot(self, client, admin_headers, beneficiario_fixture):
        """Detail returns all sections."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.get(f"/api/admin/beneficiarios/{ben_id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "beneficiario" in data
        assert "tutores" in data
        assert "estudio" in data
        assert "solicitud" in data
        assert "permisos" in data
        assert data["permisos"]["can_edit"] is True
        assert data["permisos"]["can_delete"] is True

    def test_detail_returns_404_for_nonexistent(self, client, admin_headers):
        """Non-existent beneficiario returns 404."""
        res = client.get("/api/admin/beneficiarios/99999", headers=admin_headers)
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH beneficiario
# ---------------------------------------------------------------------------

class TestAdminPatchBeneficiario:
    """PATCH /api/admin/beneficiarios/{id} — edit beneficiario fields."""

    def test_patch_nombres(self, client, admin_headers, beneficiario_fixture):
        """Admin can update beneficiario nombres."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.patch(
            f"/api/admin/beneficiarios/{ben_id}",
            json={"nombres": "ACTUALIZADO"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["updated"] is True
        # Verify the update
        detail = client.get(f"/api/admin/beneficiarios/{ben_id}", headers=admin_headers)
        assert "ACTUALIZADO" in (detail.json()["beneficiario"].get("nombres", "") or "")

    def test_patch_beneficiario_404(self, client, admin_headers):
        """PATCH non-existent beneficiario returns 404."""
        res = client.patch(
            "/api/admin/beneficiarios/99999",
            json={"nombres": "TEST"},
            headers=admin_headers,
        )
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH estudio
# ---------------------------------------------------------------------------

class TestAdminPatchEstudio:
    """PATCH /api/admin/beneficiarios/{id}/estudio — edit estudio fields."""

    def test_patch_estudio_sede(self, client, admin_headers, beneficiario_fixture):
        """Admin can update estudio sede."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.patch(
            f"/api/admin/beneficiarios/{ben_id}/estudio",
            json={"sede": "Nueva Sede Admin"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["updated"] is True

    def test_patch_estudio_404_for_nonexistent_beneficiario(self, client, admin_headers):
        """PATCH estudio for non-existent beneficiario returns 404."""
        res = client.patch(
            "/api/admin/beneficiarios/99999/estudio",
            json={"sede": "Test"},
            headers=admin_headers,
        )
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH solicitud
# ---------------------------------------------------------------------------

class TestAdminPatchSolicitud:
    """PATCH /api/admin/beneficiarios/{id}/solicitud — edit solicitud fields."""

    def test_patch_solicitud_prioridad(self, client, admin_headers, beneficiario_fixture):
        """Admin can update solicitud prioridad."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.patch(
            f"/api/admin/beneficiarios/{ben_id}/solicitud",
            json={"prioridad": "Alta"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["updated"] is True


# ---------------------------------------------------------------------------
# PATCH gestion (atomic)
# ---------------------------------------------------------------------------

class TestAdminPatchGestion:
    """PATCH /api/admin/beneficiarios/{id}/gestion — atomic study + solicitud update."""

    def test_patch_gestion_atomic(self, client, admin_headers, beneficiario_fixture):
        """Admin can update both estudio and solicitud atomically."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.patch(
            f"/api/admin/beneficiarios/{ben_id}/gestion",
            json={
                "sede": "Sede Gestion",
                "entidad_solicitante": "Rotary Club",
                "prioridad": "Media",
                "justificacion": "Justificacion de prueba",
            },
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["estudio_updated"] is True
        assert data["solicitud_updated"] is True


# ---------------------------------------------------------------------------
# DELETE cascade
# ---------------------------------------------------------------------------

class TestAdminDelete:
    """DELETE /api/admin/beneficiarios/{id} — hard delete cascade."""

    def test_delete_cascade_returns_count(self, client, admin_headers, beneficiario_fixture):
        """DELETE returns count of deleted records across all tables."""
        ben_id = beneficiario_fixture["beneficiario"]["id"]
        res = client.delete(f"/api/admin/beneficiarios/{ben_id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["deleted"] is True
        assert "registros_eliminados" in data
        assert data["registros_eliminados"]["beneficiarios"] == 1
        # Verify it's gone
        detail = client.get(f"/api/admin/beneficiarios/{ben_id}", headers=admin_headers)
        assert detail.status_code == 404

    def test_delete_nonexistent_returns_404(self, client, admin_headers):
        """DELETE non-existent beneficiario returns 404."""
        res = client.delete("/api/admin/beneficiarios/99999", headers=admin_headers)
        assert res.status_code == 404
