"""
Tests for guardar-borrador endpoint — borrador-maestro.

Covers:
  - validate_optional wrapper
  - POST /api/guardar-borrador CREATE mode
  - POST /api/guardar-borrador UPDATE mode
  - GET /api/borrador/{estudio_id}
  - Ownership check (403)
  - Format validation (422)
"""

import pytest


# ──────────────────────────────────────────────────────────────────────────
# Unit tests for validate_optional
# ──────────────────────────────────────────────────────────────────────────

class TestValidateOptional:
    """Unit tests for validate_optional() wrapper."""

    def test_returns_none_for_none_value(self):
        """None skips validation and returns None."""
        from validators import validate_optional, validate_nombre

        wrapped = validate_optional(validate_nombre)
        result = wrapped(None)
        assert result is None

    def test_returns_empty_for_empty_string(self):
        """Empty string skips validation and returns ''."""
        from validators import validate_optional, validate_telefono

        wrapped = validate_optional(validate_telefono)
        result = wrapped("")
        assert result == ""

    def test_calls_validator_for_non_empty(self):
        """Non-empty value goes through the original validator."""
        from validators import validate_optional, validate_nombre

        wrapped = validate_optional(validate_nombre)
        result = wrapped("Juan")
        assert result == "Juan"

    def test_raises_for_invalid_non_empty(self):
        """Non-empty invalid value raises from the original validator."""
        from validators import validate_optional, validate_nombre

        wrapped = validate_optional(validate_nombre)
        with pytest.raises(ValueError):
            wrapped("A")  # too short

    def test_works_with_catalog_validator(self):
        """Catalog validator wrapped with validate_optional works for None/valid/invalid."""
        from validators import validate_optional, validate_sexo

        wrapped = validate_optional(validate_sexo)
        assert wrapped(None) is None
        assert wrapped("") == ""
        assert wrapped("M") == "M"
        with pytest.raises(ValueError):
            wrapped("X")

    def test_works_with_numeric_validator(self):
        """Numeric validator wrapped with validate_optional skips None."""
        from validators import validate_optional, validate_edad_tutor

        wrapped = validate_optional(validate_edad_tutor)
        assert wrapped(None) is None
        assert wrapped(35) == 35
        with pytest.raises(ValueError):
            wrapped(150)


# ──────────────────────────────────────────────────────────────────────────
# Integration tests for POST /api/guardar-borrador (CREATE mode)
# ──────────────────────────────────────────────────────────────────────────

class TestCrearBorrador:
    """Integration tests for creating a new borrador."""

    def test_create_with_all_empty_fields_returns_201(self, client, capturista_headers, region_lon):
        """CREATE mode: all null fields → 201 (folio ya no se genera; CURP es el identificador)."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["estudio_id"] > 0
        assert data["solicitud_id"] > 0
        assert data["beneficiario_id"] > 0
        # Issue #32: folio column dropped; CURP is the natural identifier.
        assert "curp" in data
        assert data["status"] == "borrador"

    def test_create_with_partial_beneficiario_data(self, client, capturista_headers, region_lon):
        """CREATE mode: partial valid beneficiario data → 201."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "María",
            "apellido_paterno": "García",
            "apellido_materno": "López",
            "fecha_nacimiento": "2010-06-15",
            "sexo": "F",
            "telefonos": "4629876543",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["beneficiario_id"] > 0

    def test_create_with_tutor1_data(self, client, capturista_headers, region_lon):
        """CREATE mode: include tutor 1 data → 201."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "Beneficiario",
            "apellido_paterno": "Test",
            "apellido_materno": "Tutor",
            "fecha_nacimiento": "2005-03-20",
            "sexo": "M",
            "telefonos": "4621112233",
            "tutor1_nombres": "Tutor",
            "tutor1_apellido_paterno": "Principal",
            "tutor1_apellido_materno": "Uno",
            "tutor1_edad": 40,
            "tutor1_nivel_estudios": "LICENCIATURA",
            "tutor1_estado_civil": "CASADO",
            "tutor1_vivienda": "PROPIA",
            "tutor1_imss_estatus": "SI",
            "tutor1_infonavit_estatus": "NO",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["estudio_id"] > 0

    def test_format_validation_rejects_invalid_telefono(self, client, capturista_headers, region_lon):
        """Format validation: invalid telefono → 422."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "telefonos": "ABC",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"

    def test_format_validation_rejects_invalid_nombres(self, client, capturista_headers, region_lon):
        """Format validation: nombres with digits → 422."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "12345",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"

    def test_format_validation_rejects_invalid_sexo(self, client, capturista_headers, region_lon):
        """Format validation: sexo outside catalog → 422."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "sexo": "X",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"

    def test_missing_region_id_returns_422(self, client, capturista_headers):
        """CREATE mode without region_id → 422."""
        payload = {
            "sede": "León sede Forum",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"


# ──────────────────────────────────────────────────────────────────────────
# Integration tests for POST /api/guardar-borrador (UPDATE mode)
# ──────────────────────────────────────────────────────────────────────────

class TestActualizarBorrador:
    """Integration tests for updating an existing borrador."""

    def _create_borrador(self, client, capturista_headers, region_lon) -> dict:
        """Helper: create a minimal borrador and return its IDs."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "Original",
            "apellido_paterno": "Name",
            "apellido_materno": "Test",
            "fecha_nacimiento": "2000-01-01",
            "sexo": "M",
            "telefonos": "4620000000",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )
        assert res.status_code == 201
        return res.json()

    def test_update_existing_borrador(self, client, capturista_headers, region_lon):
        """UPDATE mode: change beneficiario fields on existing borrador."""
        ids = self._create_borrador(client, capturista_headers, region_lon)

        update_payload = {
            "estudio_id": ids["estudio_id"],
            "solicitud_id": ids["solicitud_id"],
            "beneficiario_id": ids["beneficiario_id"],
            "nombres": "Actualizado",
            "apellido_paterno": "Nuevo",
            "telefonos": "4621111111",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=update_payload,
            headers=capturista_headers,
        )

        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["estudio_id"] == ids["estudio_id"]

    def test_update_adds_tutor(self, client, capturista_headers, region_lon):
        """UPDATE mode: add tutor data to existing borrador."""
        ids = self._create_borrador(client, capturista_headers, region_lon)

        update_payload = {
            "estudio_id": ids["estudio_id"],
            "solicitud_id": ids["solicitud_id"],
            "beneficiario_id": ids["beneficiario_id"],
            "tutor1_nombres": "Nuevo",
            "tutor1_apellido_paterno": "Tutor",
            "tutor1_apellido_materno": "Agregado",
            "tutor1_edad": 38,
            "tutor1_nivel_estudios": "LICENCIATURA",
            "tutor1_estado_civil": "SOLTERO",
            "tutor1_vivienda": "RENTADA",
            "tutor1_imss_estatus": "NO",
            "tutor1_infonavit_estatus": "NO",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=update_payload,
            headers=capturista_headers,
        )

        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"

    def test_update_nonexistent_estudio_returns_404(self, client, capturista_headers):
        """UPDATE mode: non-existent estudio_id → 404."""
        payload = {
            "estudio_id": 999999,
            "nombres": "Test",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )

        assert res.status_code == 404, f"Expected 404, got {res.status_code}: {res.text}"


# ──────────────────────────────────────────────────────────────────────────
# Persistencia de campos técnicos del borrador (Issue #161)
# ──────────────────────────────────────────────────────────────────────────

class TestPersistenciaTecnicaBorrador:
    """observaciones_posturales, soporte_oxigeno NULL-able e INSERT fallback."""

    def _create_borrador(self, client, capturista_headers, region_lon, extra: dict | None = None) -> dict:
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "Persistencia",
            "apellido_paterno": "Tecnica",
            "fecha_nacimiento": "2010-03-03",
            "sexo": "M",
            "telefonos": "4620001111",
        }
        payload.update(extra or {})
        res = client.post("/api/guardar-borrador", json=payload, headers=capturista_headers)
        assert res.status_code == 201, f"Creation failed: {res.text}"
        return res.json()

    def test_observaciones_posturales_roundtrip_create(self, client, capturista_headers, region_lon):
        """CREATE persiste observaciones_posturales y GET /borrador la devuelve.

        Antes de la migración 0029 este campo no tenía columna (0013 renombró la
        original a `padecimiento`) y el texto del textarea se perdía SIEMPRE.
        """
        ids = self._create_borrador(
            client, capturista_headers, region_lon,
            {"observaciones_posturales": "Escoliosis leve observada"},
        )

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        assert res.status_code == 200, res.text
        solicitud = res.json()["solicitud"]
        # normalize_text: mayúsculas + sin diacríticos
        assert solicitud["observaciones_posturales"] == "ESCOLIOSIS LEVE OBSERVADA"

    def test_observaciones_posturales_update_patches(self, client, capturista_headers, region_lon):
        """UPDATE mode actualiza observaciones_posturales vía _patch_solicitud."""
        ids = self._create_borrador(
            client, capturista_headers, region_lon,
            {"observaciones_posturales": "Texto original"},
        )

        res = client.post(
            "/api/guardar-borrador",
            json={
                "estudio_id": ids["estudio_id"],
                "solicitud_id": ids["solicitud_id"],
                "observaciones_posturales": "Texto actualizado",
            },
            headers=capturista_headers,
        )
        assert res.status_code == 201, res.text

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        assert res.json()["solicitud"]["observaciones_posturales"] == "TEXTO ACTUALIZADO"

    def test_soporte_oxigeno_none_stays_null(self, client, capturista_headers, region_lon):
        """CREATE sin soporte_oxigeno → NULL en BD (no FALSE sintético).

        Antes, bool(None) → FALSE hacía indistinguible "sin responder" de un
        "No" real y anulaba la validación de completitud del issue #162.
        """
        ids = self._create_borrador(client, capturista_headers, region_lon)

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        assert res.status_code == 200, res.text
        assert res.json()["solicitud"]["soporte_oxigeno"] is None

    def test_soporte_oxigeno_false_explicito_persiste(self, client, capturista_headers, region_lon):
        """CREATE con soporte_oxigeno=false explícito guarda FALSE, no NULL."""
        ids = self._create_borrador(
            client, capturista_headers, region_lon, {"soporte_oxigeno": False}
        )

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        assert res.json()["solicitud"]["soporte_oxigeno"] is False

    def test_update_estudio_sin_solicitud_inserta_solicitud(
        self, client, capturista_headers, _test_db_conn, region_lon
    ):
        """UPDATE sobre estudio sin solicitud → INSERT fallback, no descarte silencioso.

        Antes: los campos técnicos se omitían en silencio y la respuesta traía
        solicitud_id=0 (falsy), así que el frontend nunca guardaba el id y el
        usuario perdía toda la sección técnica creyendo que se había guardado.
        """
        ids = self._create_borrador(client, capturista_headers, region_lon)

        # Simular un borrador legacy sin solicitud (p. ej., creado por POST /estudios)
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM solicitudes_tecnicas WHERE beneficiario_id = %s",
                (ids["beneficiario_id"],),
            )
        _test_db_conn.commit()

        res = client.post(
            "/api/guardar-borrador",
            json={
                "estudio_id": ids["estudio_id"],
                "entorno": "Urbano / Interiores",
                "control_tronco": "Completo",
                "peso_kg": "38.500",
                "soporte_oxigeno": True,
            },
            headers=capturista_headers,
        )
        assert res.status_code == 201, res.text
        assert res.json()["solicitud_id"] > 0

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        solicitud = res.json()["solicitud"]
        assert solicitud is not None, "La solicitud debió reinsertarse"
        assert solicitud["entorno"] == "Urbano / Interiores"
        assert solicitud["control_tronco"] == "Completo"
        assert float(solicitud["peso_kg"]) == 38.5
        assert solicitud["soporte_oxigeno"] is True

    def test_get_borrador_resolves_solicitud_urls(self, client, capturista_headers, region_lon):
        """GET /borrador expone foto_url_resolved y estudio_clinico_url_resolved
        en la solicitud para que los previews rendericen tras hidratar."""
        ids = self._create_borrador(
            client, capturista_headers, region_lon,
            {
                "foto_url": "storage://fotos-tecnica/test/foto-borrador.jpg",
                "estudio_clinico_url": "storage://documentos-estudio/test/estudio.pdf",
                "estudio_clinico_path": "test/estudio.pdf",
            },
        )

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        assert res.status_code == 200, res.text
        solicitud = res.json()["solicitud"]
        assert solicitud["foto_url_resolved"], "foto_url_resolved ausente o vacío"
        assert solicitud["foto_url_resolved"].startswith("http")
        assert solicitud["estudio_clinico_url_resolved"], "estudio_clinico_url_resolved ausente"
        assert solicitud["estudio_clinico_url_resolved"].startswith("http")


# ──────────────────────────────────────────────────────────────────────────
# Issue #131: red de seguridad UniqueViolation para CURP duplicada
# ──────────────────────────────────────────────────────────────────────────

class TestCurpUniqueViolationSafetyNet:
    """La carrera concurrente de CURP duplicada (dos guardados que pasan el
    pre-check antes de que el otro inserte) debe devolver el mismo 409
    estructurado que el pre-check, no un 500 genérico. Se simula anulando el
    pre-check con monkeypatch para que el duplicado llegue hasta la UNIQUE."""

    CURP = "GOMC900101HDFNNS08"

    def _payload(self, region_id, **extra):
        p = {
            "region_id": region_id,
            "sede": "León sede Forum",
            "nombres": "Race",
            "apellido_paterno": "Curp",
            "apellido_materno": "Test",
            "sexo": "M",
            "telefonos": "4620001111",
        }
        p.update(extra)
        return p

    def _assert_409_curp_duplicada(self, res):
        assert res.status_code == 409, f"Expected 409, got {res.status_code}: {res.text}"
        detail = res.json()["detail"]
        assert detail["type"] == "curp_duplicada"
        assert detail["curp"] == self.CURP
        assert "beneficiario_existente" in detail

    def test_create_race_returns_409_estructurado(self, client, capturista_headers, region_lon, monkeypatch):
        res = client.post(
            "/api/guardar-borrador",
            json=self._payload(region_lon["id"], curp=self.CURP),
            headers=capturista_headers,
        )
        assert res.status_code == 201, res.text

        monkeypatch.setattr(
            "routers.guardar_borrador._assert_curp_disponible", lambda *a, **k: None
        )
        res = client.post(
            "/api/guardar-borrador",
            json=self._payload(region_lon["id"], curp=self.CURP),
            headers=capturista_headers,
        )
        self._assert_409_curp_duplicada(res)

    def test_update_race_returns_409_estructurado(self, client, capturista_headers, region_lon, monkeypatch):
        res = client.post(
            "/api/guardar-borrador",
            json=self._payload(region_lon["id"], curp=self.CURP),
            headers=capturista_headers,
        )
        assert res.status_code == 201, res.text

        res = client.post(
            "/api/guardar-borrador",
            json=self._payload(region_lon["id"], nombres="Otro"),
            headers=capturista_headers,
        )
        assert res.status_code == 201, res.text
        otro_estudio_id = res.json()["estudio_id"]

        # Cambiar la CURP del segundo borrador a la ya registrada, con el
        # pre-check anulado: el UPDATE choca con la UNIQUE.
        monkeypatch.setattr(
            "routers.guardar_borrador._assert_curp_disponible", lambda *a, **k: None
        )
        res = client.post(
            "/api/guardar-borrador",
            json={"estudio_id": otro_estudio_id, "curp": self.CURP},
            headers=capturista_headers,
        )
        self._assert_409_curp_duplicada(res)

    def test_precheck_sigue_activo_sin_monkeypatch(self, client, capturista_headers, region_lon):
        """Sanidad: sin simular la carrera, el pre-check responde el mismo 409."""
        res = client.post(
            "/api/guardar-borrador",
            json=self._payload(region_lon["id"], curp=self.CURP),
            headers=capturista_headers,
        )
        assert res.status_code == 201, res.text

        res = client.post(
            "/api/guardar-borrador",
            json=self._payload(region_lon["id"], curp=self.CURP),
            headers=capturista_headers,
        )
        self._assert_409_curp_duplicada(res)


# ──────────────────────────────────────────────────────────────────────────
# Integration tests for GET /api/borrador/{estudio_id}
# ──────────────────────────────────────────────────────────────────────────

class TestObtenerBorrador:
    """Integration tests for retrieving a borrador."""

    def _create_borrador(self, client, capturista_headers, region_lon) -> dict:
        """Helper: create a borrador with full data for GET testing."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "GET",
            "apellido_paterno": "Test",
            "apellido_materno": "Borrador",
            "fecha_nacimiento": "2008-05-10",
            "diagnostico": "Parálisis cerebral",
            "sexo": "F",
            "telefonos": "4623334444",
            "calle": "Calle GET",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "tutor1_nombres": "Tutor",
            "tutor1_apellido_paterno": "GET",
            "tutor1_apellido_materno": "Test",
            "tutor1_edad": 42,
            "tutor1_nivel_estudios": "LICENCIATURA",
            "tutor1_estado_civil": "CASADO",
            "tutor1_vivienda": "PROPIA",
            "tutor1_imss_estatus": "SI",
            "tutor1_infonavit_estatus": "NO",
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=capturista_headers,
        )
        assert res.status_code == 201, f"Creation failed: {res.text}"
        return res.json()

    def test_owner_gets_200_with_full_payload(self, client, capturista_headers, region_lon):
        """GET borrador: owner gets 200 with beneficiario + tutores + solicitud."""
        ids = self._create_borrador(client, capturista_headers, region_lon)

        res = client.get(
            f"/api/borrador/{ids['estudio_id']}",
            headers=capturista_headers,
        )

        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["id"] == ids["estudio_id"]
        assert data["status"] == "borrador"
        assert data["beneficiario"] is not None
        assert data["beneficiario"]["nombres"] == "GET"
        assert len(data["tutores"]) >= 1
        assert data["tutores"][0]["numero_tutor"] == 1
        assert data["tutores"][0]["imss_estatus"] == "SI"
        assert data["solicitud"] is not None
        assert data["solicitud"]["entorno"] == "Urbano / Interiores"

    def test_tutor_nombre_estructurado_round_trip(self, client, capturista_headers, region_lon):
        """Migración 0030: el nombre del tutor vuelve estructurado en GET, no
        solo compuesto — apellidos compuestos no deben requerir heurística."""
        ids = self._create_borrador(client, capturista_headers, region_lon)

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        assert res.status_code == 200, res.text
        tutor = res.json()["tutores"][0]
        assert tutor["nombres"] == "TUTOR"
        assert tutor["apellido_paterno"] == "GET"
        assert tutor["apellido_materno"] == "TEST"
        assert tutor["nombre"] == "TUTOR GET TEST"

        # UPDATE con apellido compuesto: la división por espacios lo rompería.
        update = {
            "estudio_id": ids["estudio_id"],
            "tutor1_nombres": "Maria Jose",
            "tutor1_apellido_paterno": "De La Cruz",
            "tutor1_apellido_materno": "San Juan",
            "tutor1_edad": 42,
        }
        res = client.post("/api/guardar-borrador", json=update, headers=capturista_headers)
        assert res.status_code == 201, res.text

        res = client.get(f"/api/borrador/{ids['estudio_id']}", headers=capturista_headers)
        assert res.status_code == 200, res.text
        tutor = res.json()["tutores"][0]
        assert tutor["nombres"] == "MARIA JOSE"
        assert tutor["apellido_paterno"] == "DE LA CRUZ"
        assert tutor["apellido_materno"] == "SAN JUAN"
        assert tutor["nombre"] == "MARIA JOSE DE LA CRUZ SAN JUAN"

    def test_curp_persists_and_is_recovered(self, client, capturista_headers, region_lon):
        """Issue #32: CURP saved in a draft must come back on GET (prefill)."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "CURP",
            "apellido_paterno": "Test",
            "apellido_materno": "Recupera",
            "curp": "HEGG560427MVZRRL04",
            "sexo": "M",
            "telefonos": "4625556666",
        }
        res = client.post("/api/guardar-borrador", json=payload, headers=capturista_headers)
        assert res.status_code == 201, res.text
        assert res.json()["curp"] == "HEGG560427MVZRRL04"

        got = client.get(f"/api/borrador/{res.json()['estudio_id']}", headers=capturista_headers)
        assert got.status_code == 200, got.text
        assert got.json()["beneficiario"]["curp_benef"] == "HEGG560427MVZRRL04"

    def test_non_owner_returns_403(self, client, capturista_headers, admin_headers, region_lon):
        """GET borrador: non-owner capturista gets 403."""
        # Create as capturista (using capturista_headers)
        ids = self._create_borrador(client, capturista_headers, region_lon)

        # Admin headers — admin can access any resource, so we need another capturista
        # Let's create a second capturista and try to access
        import psycopg2.extras
        from passlib.context import CryptContext
        from database import build_test_conn_kwargs

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        conn = psycopg2.connect(**build_test_conn_kwargs())
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO usuarios (nombre, email, password_hash, rol)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                ("Capturista 3", "cap3@test.mx", pwd_ctx.hash("cap3pass123"), "capturista"),
            )
        conn.commit()
        conn.close()

        # Login as capturista 3
        login_res = client.post(
            "/api/auth/login",
            json={"email": "cap3@test.mx", "password": "cap3pass123"},
        )
        assert login_res.status_code == 200
        cap3_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        res = client.get(
            f"/api/borrador/{ids['estudio_id']}",
            headers=cap3_headers,
        )

        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    def test_admin_can_access_any_borrador(self, client, capturista_headers, admin_headers, region_lon):
        """GET borrador: admin can access any borrador."""
        ids = self._create_borrador(client, capturista_headers, region_lon)

        res = client.get(
            f"/api/borrador/{ids['estudio_id']}",
            headers=admin_headers,
        )

        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    def test_returns_404_for_completed_estudio(self, client, capturista_headers, _test_db_conn, region_lon, capturista_user):
        """GET borrador: estudio with status=completo → 404."""
        import psycopg2.extras
        from database import build_test_conn_kwargs

        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Create beneficiario
            cur.execute(
                """
                INSERT INTO beneficiarios (nombre, folio, region_id, sede)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                ("COMPLETO TEST", "MX-LON-2026-099", region_lon["id"], "Sede"),
            )
            ben_id = cur.fetchone()["id"]

            # Create estudio as completo
            cur.execute(
                """
                INSERT INTO estudios_socioeconomicos
                    (beneficiario_id, usuario_id, status, fecha_estudio, sede, ciudad_registro)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ben_id, capturista_user["id"], "completo", "2026-01-01", "Sede", "CIUDAD"),
            )
            estudio_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        res = client.get(
            f"/api/borrador/{estudio_id}",
            headers=capturista_headers,
        )

        assert res.status_code == 404, f"Expected 404, got {res.status_code}: {res.text}"

    def test_returns_404_for_nonexistent_estudio(self, client, capturista_headers):
        """GET borrador: non-existent estudio_id → 404."""
        res = client.get(
            "/api/borrador/999999",
            headers=capturista_headers,
        )

        assert res.status_code == 404, f"Expected 404, got {res.status_code}: {res.text}"

    def test_unauthenticated_returns_401(self, client):
        """GET borrador: no token → 401."""
        res = client.get("/api/borrador/1")

        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


# ──────────────────────────────────────────────────────────────────────────
# Role-based access tests for POST
# ──────────────────────────────────────────────────────────────────────────

class TestRoleAccess:
    """Tests for role-based access to guardar-borrador."""

    def test_tecnico_role_returns_403_on_post(self, client, tecnico_headers, region_lon):
        """POST: tecnico role → 403 forbidden."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=tecnico_headers,
        )

        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    def test_organizacion_role_can_create(self, client, organizacion_headers, region_lon):
        """POST: organizacion role → 201."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "nombres": "Org",
            "apellido_paterno": "Test",
            "apellido_materno": "Borrador",
            "fecha_nacimiento": "2010-01-01",
            "sexo": "M",
            "telefonos": "4629998888",
        }
        res = client.post(
            "/api/guardar-borrador",
            json=payload,
            headers=organizacion_headers,
        )

        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
