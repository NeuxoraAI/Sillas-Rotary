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


class TestFolioGeneration:
    """Folio counter integration via /api/estudios (calls generate_folio inside)."""

    def test_first_beneficiario_gets_001(self, client, capturista_headers, region_lon, pais_mx):
        """First registration in MX/LON/2026 gets folio MX-LON-2026-001."""
        payload = _estudio_payload(region_lon["id"], nombre="Bene Uno")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)

        assert res.status_code == 201
        assert res.json()["folio"] == "MX-LON-2026-001"

    def test_second_beneficiario_gets_002(self, client, capturista_headers, region_lon, pais_mx):
        """Second registration in same region/year gets MX-LON-2026-002."""
        payload1 = _estudio_payload(region_lon["id"], nombre="Bene Uno")
        payload2 = _estudio_payload(region_lon["id"], nombre="Bene Dos", tel="4629999999")
        client.post("/api/estudios", json=payload1, headers=capturista_headers)
        res = client.post("/api/estudios", json=payload2, headers=capturista_headers)

        assert res.status_code == 201
        assert res.json()["folio"] == "MX-LON-2026-002"

    def test_folio_counter_independent_per_region(self, client, capturista_headers, region_lon, region_ira, pais_mx):
        """Different regions have independent counters."""
        payload_lon = _estudio_payload(region_lon["id"], nombre="Bene LON")
        payload_ira = _estudio_payload(region_ira["id"], nombre="Bene IRA", tel="4629999998")
        client.post("/api/estudios", json=payload_lon, headers=capturista_headers)
        res = client.post("/api/estudios", json=payload_ira, headers=capturista_headers)

        assert res.status_code == 201
        assert res.json()["folio"] == "MX-IRA-2026-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estudio_payload(region_id: int, nombre: str, tel: str = "4621234567") -> dict:
    """Build a minimal complete estudio payload."""
    return {
        "region_id": region_id,
        "sede": "León sede Forum",
        "beneficiario": {
            "nombre": nombre,
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "telefonos": tel,
        },
        "tutores": [
            {
                "numero_tutor": 1,
                "nombre": "Tutor Test",
                "edad": 45,
                "nivel_estudios": "Licenciatura",
                "estado_civil": "Casado",
                "num_hijos": 2,
                "vivienda": "Propia",
                "fuente_empleo": "Empleado",
                "antiguedad": "10 años",
                "ingreso_mensual": 12000.0,
                "tiene_imss": True,
                "tiene_infonavit": False,
            }
        ],
        "estudio": {
            "otras_fuentes_ingreso": "Ninguna",
            "monto_otras_fuentes": None,
            "tuvo_silla_previa": False,
            "como_obtuvo_silla": None,
            "elaboro_estudio": "Capturista Test",
            "fecha_estudio": "2026-04-18",
            "status": "completo",
        },
    }
