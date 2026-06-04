"""
TDD Tests for Perfiles de Capturista y Organización.

Tests for:
- GET /api/me/capturas (capturista sees own, org sees its own, admin sees own)
- elaboro_estudio override for organizacion role (POST and PATCH)
"""

import pytest


class TestMisCapturas:
    """GET /api/me/capturas scenarios."""

    def test_capturista_sees_own_capturas(self, client, capturista_headers, sample_estudio):
        """Capturista can GET /api/me/capturas and sees their own studies."""
        res = client.get("/api/me/capturas", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            assert "estudio_id" in item
            assert "folio" in item
            assert "beneficiario_nombre" in item
            assert "elaboro_estudio" in item
            assert "fecha_estudio" in item
            assert "status" in item
            assert "sede" in item
            assert "created_at" in item
        # All results should have capturista's own name as elaboro_estudio
        for item in data:
            assert item["elaboro_estudio"] == "Capturista Test"

    def test_organizacion_sees_own_capturas(self, client, organizacion_headers, organizacion_user, region_lon):
        """Organizacion sees their own studies (by usuario_id)."""
        # Create a study as organizacion user
        token = _get_token_from_headers(organizacion_headers)
        session_nombre = "Organización Test"
        payload = _build_minimal_estudio(region_lon["id"], session_nombre)
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201, f"Org create estudio failed: {res.text}"

        res = client.get("/api/me/capturas", headers=organizacion_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_capturista_sees_zero_capturas(self, client, capturista_headers):
        """Capturista with no studies sees empty list."""
        res = client.get("/api/me/capturas", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_unauthorized_returns_401(self, client):
        """Request without JWT returns 401."""
        res = client.get("/api/me/capturas")
        assert res.status_code == 401

    def test_tecnico_blocked_from_mis_capturas(self, client, tecnico_headers):
        """Tecnico should be blocked from GET /api/me/capturas."""
        res = client.get("/api/me/capturas", headers=tecnico_headers)
        assert res.status_code == 403

    def test_results_ordered_by_created_at_desc(self, client, capturista_headers, capturista_user, region_lon):
        """Results are sorted by created_at DESC (most recent first)."""
        # Create two studies
        payload1 = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        payload1["estudio"]["fecha_estudio"] = "2026-01-01"
        res1 = client.post("/api/estudios", json=payload1, headers=capturista_headers)
        assert res1.status_code == 201

        payload2 = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        payload2["estudio"]["fecha_estudio"] = "2026-06-01"
        res2 = client.post("/api/estudios", json=payload2, headers=capturista_headers)
        assert res2.status_code == 201

        res = client.get("/api/me/capturas", headers=capturista_headers)
        data = res.json()
        assert len(data) >= 2
        timestamps = [item["created_at"] for item in data]
        assert timestamps == sorted(timestamps, reverse=True)


class TestElaboroEstudioOverride:
    """POST/PATCH /api/estudios elaboro_estudio override for organizacion."""

    def test_capturista_elaboro_estudio_ignored(self, client, capturista_headers, region_lon):
        """Capturista's elaboro_estudio value is ignored, replaced with session nombre."""
        payload = _build_minimal_estudio(region_lon["id"], "INYECTADO")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # Verify via GET /api/me/capturas
        res = client.get("/api/me/capturas", headers=capturista_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        assert estudio["elaboro_estudio"] == "Capturista Test"  # usuario.nombre, NOT "INYECTADO"

    def test_organizacion_elaboro_estudio_accepted(self, client, organizacion_headers, region_lon):
        """Organizacion's elaboro_estudio value is accepted from the client."""
        volunteer_name = "María López"
        expected_name = "MARIA LOPEZ"  # normalized by normalize_text
        payload = _build_minimal_estudio(region_lon["id"], volunteer_name)
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201, f"Org create estudio failed: {res.text}"
        estudio_id = res.json()["estudio_id"]

        # Verify via GET /api/me/capturas
        res = client.get("/api/me/capturas", headers=organizacion_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        assert estudio["elaboro_estudio"] == expected_name

    def test_organizacion_empty_elaboro_estudio_falls_back_to_org_name(self, client, organizacion_headers, region_lon):
        """Organizacion with empty elaboro_estudio falls back to org account name."""
        payload = _build_minimal_estudio(region_lon["id"], "")
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        res = client.get("/api/me/capturas", headers=organizacion_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        assert estudio["elaboro_estudio"] == "Organización Test"

    def test_organizacion_long_name_falls_back(self, client, organizacion_headers, region_lon):
        """Long elaboro_estudio (>120 chars) falls back to org account name."""
        long_name = "A" * 200
        payload = _build_minimal_estudio(region_lon["id"], long_name)
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        res = client.get("/api/me/capturas", headers=organizacion_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        # Should fall back to org account name (not the long value)
        assert estudio["elaboro_estudio"] == "Organización Test"

    def test_patch_organizacion_elaboro_estudio_accepted(self, client, organizacion_headers, region_lon):
        """PATCH /estudios accepts elaboro_estudio for organizacion."""
        # Create study first
        payload = _build_minimal_estudio(region_lon["id"], "Initial Name")
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # Now PATCH with new elaboro_estudio
        patch_payload = {
            "elaboro_estudio": "Ana Vega Actualizado",
            "status": "borrador",
        }
        res = client.patch(f"/api/estudios/{estudio_id}", json=patch_payload, headers=organizacion_headers)
        assert res.status_code == 200

        # Verify the update
        res = client.get(f"/api/estudios/{estudio_id}", headers=organizacion_headers)
        data = res.json()
        assert data["elaboro_estudio"] == "ANA VEGA ACTUALIZADO"  # normalized by normalize_text

    def test_patch_capturista_elaboro_estudio_ignored(self, client, capturista_headers, region_lon):
        """PATCH /estudios ignores elaboro_estudio for capturista."""
        payload = _build_minimal_estudio(region_lon["id"], "Ignored")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # PATCH with different elaboro_estudio
        patch_payload = {
            "elaboro_estudio": "Should Be Ignored",
            "status": "borrador",
        }
        res = client.patch(f"/api/estudios/{estudio_id}", json=patch_payload, headers=capturista_headers)
        assert res.status_code == 200

        res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        data = res.json()
        assert data["elaboro_estudio"] == "Capturista Test"


# ═══════════════════════════════════════════════════════════════════════════════
# New Tests for GitHub-style Profiles (Tasks 8.1–8.4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMePerfil:
    """GET /api/me/perfil and PATCH /api/me/perfil endpoints."""

    def test_get_my_perfil_returns_capturista_data(self, client, capturista_headers, capturista_user):
        """GET /api/me/perfil returns usuario info and stats."""
        res = client.get("/api/me/perfil", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["usuario"]["id"] == capturista_user["id"]
        assert data["usuario"]["nombre"] == "Capturista Test"
        assert data["usuario"]["rol"] == "capturista"
        assert "stats" in data
        assert "total_capturas" in data["stats"]
        assert "this_month" in data["stats"]
        assert "heatmap_data" in data
        assert data["can_edit"] is True

    def test_get_my_perfil_with_no_studies(self, client, capturista_headers):
        """GET /api/me/perfil with no studies shows zero stats."""
        res = client.get("/api/me/perfil", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["stats"]["total_capturas"] == 0
        assert data["heatmap_data"] == []

    def test_get_my_perfil_requires_auth(self, client):
        """GET /api/me/perfil without JWT returns 401."""
        res = client.get("/api/me/perfil")
        assert res.status_code == 401

    def test_patch_my_perfil_updates_nombre(self, client, capturista_headers):
        """PATCH /api/me/perfil updates nombre."""
        res = client.patch("/api/me/perfil", json={"nombre": "Updated Name"}, headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["nombre"] == "Updated Name"

    def test_patch_my_perfil_duplicate_email_returns_409(self, client, capturista_headers, admin_headers):
        """PATCH /api/me/perfil with duplicate email returns 409."""
        res = client.patch("/api/me/perfil", json={"email": "admin@test.mx"}, headers=capturista_headers)
        assert res.status_code == 409

    def test_patch_my_perfil_short_nombre_returns_422(self, client, capturista_headers):
        """PATCH /api/me/perfil with too-short nombre returns 422."""
        res = client.patch("/api/me/perfil", json={"nombre": "A"}, headers=capturista_headers)
        assert res.status_code == 422


class TestMeHeatmap:
    """GET /api/me/heatmap endpoint."""

    def test_heatmap_empty_with_no_studies(self, client, capturista_headers):
        """GET /api/me/heatmap with no studies returns empty array."""
        res = client.get("/api/me/heatmap", headers=capturista_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_heatmap_returns_date_count_pairs(self, client, capturista_headers, capturista_user, region_lon):
        """GET /api/me/heatmap with studies returns date-count pairs."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.get("/api/me/heatmap", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        for entry in data:
            assert "date" in entry
            assert "count" in entry
            assert entry["count"] >= 1

    def test_heatmap_groups_same_date(self, client, capturista_headers, capturista_user, region_lon):
        """Multiple studies on same date are grouped."""
        for _ in range(2):
            payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
            client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.get("/api/me/heatmap", headers=capturista_headers)
        data = res.json()
        from datetime import date
        today = str(date.today())
        today_entry = next((e for e in data if e["date"] == today), None)
        if today_entry:
            assert today_entry["count"] >= 2

    def test_heatmap_sorted_by_date(self, client, capturista_headers, capturista_user, region_lon):
        """Heatmap entries are sorted by date ascending."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.get("/api/me/heatmap", headers=capturista_headers)
        data = res.json()
        if len(data) > 1:
            dates = [e["date"] for e in data]
            assert dates == sorted(dates)


class TestMeBeneficiarios:
    """GET /api/me/beneficiarios endpoint."""

    def test_beneficiarios_returns_user_studies(self, client, capturista_headers, capturista_user, region_lon):
        """GET /api/me/beneficiarios returns this user's beneficiaries."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201

        res = client.get("/api/me/beneficiarios", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        for item in data:
            assert "estudio_id" in item
            assert "folio" in item
            assert "beneficiario_nombre" in item
            assert "status" in item
            assert "edit_url" in item
            assert f"estudio_id={item['estudio_id']}" in item["edit_url"]

    def test_beneficiarios_empty(self, client, capturista_headers):
        """GET /api/me/beneficiarios with no studies returns empty list."""
        res = client.get("/api/me/beneficiarios", headers=capturista_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_beneficiarios_blocked_for_tecnico(self, client, tecnico_headers):
        """Tecnico cannot access beneficiary list."""
        res = client.get("/api/me/beneficiarios", headers=tecnico_headers)
        assert res.status_code == 403


class TestOrganizacionesCRUD:
    """Organization CRUD endpoints (admin only)."""

    def _create_org(self, client, admin_headers, nombre="Test Org Rotary"):
        return client.post(
            "/api/organizaciones",
            json={"nombre": nombre, "direccion": "Dirección Test"},
            headers=admin_headers,
        )

    def test_admin_creates_org(self, client, admin_headers):
        """Admin can create an organization (201)."""
        res = self._create_org(client, admin_headers, "Rotary León Test")
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["nombre"] == "Rotary León Test"

    def test_non_admin_cannot_create_org(self, client, capturista_headers):
        """Non-admin creating org returns 403."""
        res = self._create_org(client, capturista_headers, "Should Fail")
        assert res.status_code == 403

    def test_duplicate_org_name_returns_409(self, client, admin_headers):
        """Duplicate org name returns 409."""
        self._create_org(client, admin_headers, "Unique Name Org")
        res = self._create_org(client, admin_headers, "Unique Name Org")
        assert res.status_code == 409

    def test_admin_lists_orgs(self, client, admin_headers):
        """Admin can list all organizations."""
        self._create_org(client, admin_headers, "Org Alpha")
        self._create_org(client, admin_headers, "Org Beta")

        res = client.get("/api/organizaciones", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 2

    def test_admin_assigns_leader(self, client, admin_headers, capturista_user):
        """Admin assigns a leader to an org."""
        res = self._create_org(client, admin_headers, "Leader Test Org")
        org_id = res.json()["id"]

        res = client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["lider_usuario_id"] == capturista_user["id"]

    def test_admin_removes_leader(self, client, admin_headers, capturista_user):
        """Admin removes a leader by setting to null."""
        res = self._create_org(client, admin_headers, "Remove Leader Org")
        org_id = res.json()["id"]

        client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        res = client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": None},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["lider_usuario_id"] is None

    def test_get_org_detail(self, client, admin_headers, capturista_user):
        """GET /api/organizaciones/{id} returns org detail with stats."""
        res = self._create_org(client, admin_headers, "Detail Test Org")
        org_id = res.json()["id"]

        client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )

        res = client.get(f"/api/organizaciones/{org_id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["nombre"] == "Detail Test Org"
        assert "lider_usuario_id" in data
        assert "stats" in data
        assert "total_capturas" in data["stats"]
        assert "this_month" in data["stats"]

    def test_get_org_detail_not_found(self, client, admin_headers):
        """GET /api/organizaciones/{id} for non-existent org returns 404."""
        res = client.get("/api/organizaciones/99999", headers=admin_headers)
        assert res.status_code == 404

    def test_voluntarios_empty_for_unlinked_org(self, client, admin_headers):
        """GET /api/organizaciones/{id}/voluntarios returns empty for unlinked org."""
        res = self._create_org(client, admin_headers, "Voluntarios Test Org")
        org_id = res.json()["id"]

        res = client.get(f"/api/organizaciones/{org_id}/voluntarios", headers=admin_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_create_org_with_usuario_id(self, client, admin_headers, capturista_user):
        """Admin creates org with linked user account."""
        res = client.post(
            "/api/organizaciones",
            json={"nombre": "Org with User", "usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        assert res.status_code == 201


class TestLeaderBypass:
    """Leader authorization bypass scenarios."""

    def test_non_leader_blocked_from_patch(self, client, capturista_headers, tecnico_headers, region_lon):
        """Non-leader PATCHing otro's estudio returns 403."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # Try to PATCH as a different user (tecnico)
        res = client.patch(
            f"/api/estudios/{estudio_id}",
            json={"status": "borrador"},
            headers=tecnico_headers,
        )
        assert res.status_code == 403


class TestOrgHeatmap:
    """Organization heatmap endpoints."""

    def test_org_heatmap_empty(self, client, admin_headers):
        """GET /api/organizaciones/{id}/heatmap with no studies returns empty."""
        import uuid
        unique = str(uuid.uuid4())[:8]
        res = client.post(
            "/api/organizaciones",
            json={"nombre": f"Heatmap Empty {unique}"},
            headers=admin_headers,
        )
        org_id = res.json()["id"]

        res = client.get(f"/api/organizaciones/{org_id}/heatmap", headers=admin_headers)
        assert res.status_code == 200
        assert res.json() == []


class TestProfileUpdateEdgeCases:
    """Edge cases for profile updates."""

    def test_patch_empty_body_returns_current(self, client, capturista_headers):
        """PATCH with empty body returns current profile."""
        res = client.patch("/api/me/perfil", json={}, headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert "nombre" in data


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_token_from_headers(headers: dict) -> str:
    """Extract Bearer token from headers dict."""
    auth = headers.get("Authorization", "")
    return auth.replace("Bearer ", "")


def _build_minimal_estudio(region_id: int, elaboro_estudio: str) -> dict:
    """Build a minimal estudio payload for testing."""
    return {
        "region_id": region_id,
        "sede": "Sede Test",
        "beneficiario": {
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "TEST",
            "apellido_materno": "PERFILES",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "num_ext": "12A",
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
                "nombres": "Tutor",
                "apellido_paterno": "Test",
                "apellido_materno": "Perfiles",
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "fuente_empleo": "Empleado",
                "antiguedad_anios": 10,
                "ingreso_mensual": 12000,
                "tiene_imss": True,
                "tiene_infonavit": False,
            }
        ],
        "estudio": {
            "tuvo_silla_previa": False,
            "como_obtuvo_silla": None,
            "elaboro_estudio": elaboro_estudio,
            "fecha_estudio": "2026-06-01",
            "status": "completo",
        },
        "ciudad_registro": "LEON, GTO",
    }
