"""
Integration tests for region catalog and folio generation.

TDD: Tests written BEFORE implementation.
Spec reference: region-catalog + folio-generation (fase-1-fundacion).
"""

import pytest


class TestPaises:
    """POST /api/paises + GET /api/paises."""

    def test_admin_creates_pais(self, client, admin_headers):
        """Admin can create a country."""
        res = client.post("/api/paises", json={
            "nombre": "México",
            "codigo": "MX",
        }, headers=admin_headers)

        assert res.status_code == 201
        data = res.json()
        assert data["nombre"] == "México"
        assert data["codigo"] == "MX"
        assert data["activo"] is True
        assert "pais_id" in data

    def test_list_paises_returns_active_countries(self, client, admin_headers, pais_mx, pais_us):
        """GET /api/paises returns all active countries."""
        res = client.get("/api/paises", headers=admin_headers)

        assert res.status_code == 200
        data = res.json()
        codigos = [p["codigo"] for p in data]
        assert "MX" in codigos
        assert "US" in codigos

    def test_duplicate_pais_codigo_returns_409(self, client, admin_headers, pais_mx):
        """Duplicate country code returns 409."""
        res = client.post("/api/paises", json={
            "nombre": "Mexico Otro",
            "codigo": "MX",  # already exists
        }, headers=admin_headers)

        assert res.status_code == 409


class TestRegiones:
    """POST /api/regiones + GET /api/regiones."""

    def test_admin_creates_region(self, client, admin_headers, pais_mx):
        """Admin can create a region within a country."""
        res = client.post("/api/regiones", json={
            "pais_id": pais_mx["id"],
            "nombre": "León, Gto",
            "codigo": "LON",
        }, headers=admin_headers)

        assert res.status_code == 201
        data = res.json()
        assert data["codigo"] == "LON"
        assert data["nombre"] == "León, Gto"
        assert data["pais_id"] == pais_mx["id"]
        assert data["activo"] is True
        assert "region_id" in data

    def test_list_regiones_filters_by_pais(self, client, admin_headers, pais_mx, pais_us, region_lon):
        """GET /api/regiones?pais_id=X returns only that country's active regions."""
        # Add a US region
        client.post("/api/regiones", json={
            "pais_id": pais_us["id"],
            "nombre": "Pearland, TX",
            "codigo": "PRL",
        }, headers=admin_headers)

        res = client.get(f"/api/regiones?pais_id={pais_mx['id']}", headers=admin_headers)

        assert res.status_code == 200
        data = res.json()
        # Only MX regions
        assert all(r["pais_id"] == pais_mx["id"] for r in data)
        # region_lon should be there
        assert any(r["codigo"] == "LON" for r in data)
        # US region should NOT be there
        assert not any(r["codigo"] == "PRL" for r in data)

    def test_list_regiones_excludes_inactive(self, client, admin_headers, pais_mx, region_lon, _test_db_conn):
        """Inactive regions are excluded from list."""
        # Deactivate the region
        with _test_db_conn.cursor() as cur:
            cur.execute("UPDATE regiones SET activo = FALSE WHERE id = %s", (region_lon["id"],))
        _test_db_conn.commit()

        res = client.get(f"/api/regiones?pais_id={pais_mx['id']}", headers=admin_headers)
        data = res.json()
        assert not any(r["region_id"] == region_lon["id"] for r in data)

    def test_duplicate_region_codigo_same_pais_returns_409(self, client, admin_headers, pais_mx, region_lon):
        """Duplicate region code within same country returns 409."""
        res = client.post("/api/regiones", json={
            "pais_id": pais_mx["id"],
            "nombre": "León otro",
            "codigo": "LON",  # already exists for MX
        }, headers=admin_headers)

        assert res.status_code == 409

    def test_same_codigo_different_pais_allowed(self, client, admin_headers, pais_mx, pais_us):
        """Same region code is allowed for different countries."""
        client.post("/api/regiones", json={
            "pais_id": pais_mx["id"],
            "nombre": "X Ciudad MX",
            "codigo": "XCX",
        }, headers=admin_headers)

        res = client.post("/api/regiones", json={
            "pais_id": pais_us["id"],
            "nombre": "X Ciudad US",
            "codigo": "XCX",  # same code, different country → OK
        }, headers=admin_headers)

        assert res.status_code == 201


class TestUpdatePais:
    """PATCH /api/paises/{id} — admin only."""

    def test_admin_edits_pais_nombre(self, client, admin_headers, pais_mx):
        """Admin can rename a country."""
        res = client.patch(f"/api/paises/{pais_mx['id']}", json={"nombre": "México Renombrado"}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["nombre"] == "México Renombrado"

    def test_admin_deactivates_pais(self, client, admin_headers, pais_mx):
        """Admin can deactivate a country."""
        res = client.patch(f"/api/paises/{pais_mx['id']}", json={"activo": False}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["activo"] is False

    def test_admin_reactivates_pais(self, client, admin_headers, pais_mx):
        """Admin can reactivate a deactivated country."""
        client.patch(f"/api/paises/{pais_mx['id']}", json={"activo": False}, headers=admin_headers)
        res = client.patch(f"/api/paises/{pais_mx['id']}", json={"activo": True}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["activo"] is True

    def test_admin_edits_pais_codigo_without_folios(self, client, admin_headers, pais_mx):
        """Admin can change codigo when no folios exist for it."""
        res = client.patch(f"/api/paises/{pais_mx['id']}", json={"codigo": "MXX"}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["codigo"] == "MXX"

    def test_codigo_change_blocked_when_folios_exist(self, client, admin_headers, pais_mx, region_lon,
                                                      capturista_headers):
        """Changing codigo is rejected when region_counters already has rows for that code."""
        payload = _estudio_payload(region_lon["id"], nombre="Bene Folio")
        client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.patch(f"/api/paises/{pais_mx['id']}", json={"codigo": "MXX"}, headers=admin_headers)
        assert res.status_code == 409
        assert "folio" in res.json()["detail"].lower()

    def test_duplicate_codigo_on_edit_returns_409(self, client, admin_headers, pais_mx, pais_us):
        """Editing a pais codigo to a taken code returns 409."""
        res = client.patch(f"/api/paises/{pais_mx['id']}", json={"codigo": "US"}, headers=admin_headers)
        assert res.status_code == 409

    def test_nonexistent_pais_returns_404(self, client, admin_headers):
        """PATCH on non-existent pais returns 404."""
        res = client.patch("/api/paises/99999", json={"nombre": "No existe"}, headers=admin_headers)
        assert res.status_code == 404

    def test_capturista_cannot_edit_pais(self, client, capturista_headers, pais_mx):
        """Non-admin cannot edit paises -> 401 or 403."""
        res = client.patch(f"/api/paises/{pais_mx['id']}", json={"nombre": "Hack"}, headers=capturista_headers)
        assert res.status_code in (401, 403)


class TestUpdateRegion:
    """PATCH /api/regiones/{id} — admin only."""

    def test_admin_edits_region_nombre(self, client, admin_headers, region_lon):
        """Admin can rename a region."""
        res = client.patch(f"/api/regiones/{region_lon['id']}", json={"nombre": "León Renombrado"}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["nombre"] == "León Renombrado"

    def test_admin_deactivates_region(self, client, admin_headers, region_lon):
        """Admin can deactivate a region."""
        res = client.patch(f"/api/regiones/{region_lon['id']}", json={"activo": False}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["activo"] is False

    def test_admin_reactivates_region(self, client, admin_headers, region_lon):
        """Admin can reactivate a deactivated region."""
        client.patch(f"/api/regiones/{region_lon['id']}", json={"activo": False}, headers=admin_headers)
        res = client.patch(f"/api/regiones/{region_lon['id']}", json={"activo": True}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["activo"] is True

    def test_admin_edits_region_codigo_without_folios(self, client, admin_headers, region_lon):
        """Admin can change region codigo when no folios exist for it."""
        res = client.patch(f"/api/regiones/{region_lon['id']}", json={"codigo": "LNX"}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["codigo"] == "LNX"

    def test_region_codigo_change_blocked_when_folios_exist(self, client, admin_headers, region_lon,
                                                              pais_mx, capturista_headers):
        """Changing region codigo is rejected when region_counters already has rows."""
        payload = _estudio_payload(region_lon["id"], nombre="Bene Folio Region")
        client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.patch(f"/api/regiones/{region_lon['id']}", json={"codigo": "LNX"}, headers=admin_headers)
        assert res.status_code == 409
        assert "folio" in res.json()["detail"].lower()

    def test_duplicate_codigo_within_pais_on_edit_returns_409(self, client, admin_headers, pais_mx, region_lon, region_ira):
        """Editing a region codigo to an already-taken code within the same pais returns 409."""
        res = client.patch(f"/api/regiones/{region_lon['id']}", json={"codigo": "IRA"}, headers=admin_headers)
        assert res.status_code == 409

    def test_nonexistent_region_returns_404(self, client, admin_headers):
        """PATCH on non-existent region returns 404."""
        res = client.patch("/api/regiones/99999", json={"nombre": "No existe"}, headers=admin_headers)
        assert res.status_code == 404

    def test_capturista_cannot_edit_region(self, client, capturista_headers, region_lon):
        """Non-admin cannot edit regiones -> 401 or 403."""
        res = client.patch(f"/api/regiones/{region_lon['id']}", json={"nombre": "Hack"}, headers=capturista_headers)
        assert res.status_code in (401, 403)


class TestListWithInactive:
    """GET /api/paises?include_inactive=true and GET /api/regiones?include_inactive=true."""

    def test_admin_sees_inactive_paises(self, client, admin_headers, pais_mx, _test_db_conn):
        """Admin with include_inactive=true sees deactivated countries."""
        with _test_db_conn.cursor() as cur:
            cur.execute("UPDATE paises SET activo = FALSE WHERE id = %s", (pais_mx["id"],))
        _test_db_conn.commit()

        res = client.get("/api/paises?include_inactive=true", headers=admin_headers)
        assert res.status_code == 200
        ids = [p["pais_id"] for p in res.json()]
        assert pais_mx["id"] in ids

    def test_non_admin_cannot_see_inactive_paises(self, client, capturista_headers, pais_mx, _test_db_conn):
        """Non-admin ignores include_inactive=true — only active countries returned."""
        with _test_db_conn.cursor() as cur:
            cur.execute("UPDATE paises SET activo = FALSE WHERE id = %s", (pais_mx["id"],))
        _test_db_conn.commit()

        res = client.get("/api/paises?include_inactive=true", headers=capturista_headers)
        assert res.status_code == 200
        ids = [p["pais_id"] for p in res.json()]
        assert pais_mx["id"] not in ids


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estudio_payload(region_id: int, nombre: str, tel: str = "4621234567") -> dict:
    """Build a minimal complete estudio payload matching current API contract."""
    return {
        "region_id": region_id,
        "sede": "León sede Forum",
        "ciudad_registro": "LEON, GTO",
        "beneficiario": {
            "nombres": nombre,
            "apellido_paterno": "TEST",
            "apellido_materno": "MUESTRA",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "PARALISIS CEREBRAL",
            "calle": "CALLE TEST 123",
            "num_ext": "12A",
            "colonia": "CENTRO",
            "ciudad": "LEON",
            "estado_codigo": "11",
            "sexo": "M",
            "telefonos": tel,
        },
        "tutores": [
            {
                "numero_tutor": 1,
                "nombres": "TUTOR",
                "apellido_paterno": "TEST",
                "apellido_materno": "MUESTRA",
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "fuente_empleo": "EMPLEADO",
                "ingreso_mensual": 12000,
                "tiene_imss": True,
                "tiene_infonavit": False,
            }
        ],
        "estudio": {
            "otras_fuentes_ingreso": "NINGUNA",
            "monto_otras_fuentes": None,
            "tuvo_silla_previa": False,
            "como_obtuvo_silla": None,
            "elaboro_estudio": "CAPTURISTA TEST",
            "fecha_estudio": "2026-04-18",
            "status": "completo",
        },
    }
