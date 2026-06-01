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
        payload = _build_minimal_estudio(region_lon["id"], volunteer_name)
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201, f"Org create estudio failed: {res.text}"
        estudio_id = res.json()["estudio_id"]

        # Verify via GET /api/me/capturas
        res = client.get("/api/me/capturas", headers=organizacion_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        assert estudio["elaboro_estudio"] == volunteer_name

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
        assert data["elaboro_estudio"] == "Ana Vega Actualizado"

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
