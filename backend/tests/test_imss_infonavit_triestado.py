"""
Tests for PR3: IMSS/INFONAVIT Triestado con Radio Buttons.

Strict TDD: These tests are written BEFORE implementation.
They reference functions and fields that do NOT exist yet (RED phase).
"""

import pytest


# =============================================================================
# TASK-14: Status Mapping Functions (Unit Tests)
# =============================================================================

class TestStatusMappingFunctions:
    """Unit tests for _mapear_a_db (status_to_db) and _mapear_de_db (db_to_status)."""

    def test_status_to_db_si_returns_1(self):
        """SI status maps to integer 1 in the database."""
        from routers.socioeconomico import _mapear_a_db
        assert _mapear_a_db("SI") == 1

    def test_status_to_db_no_returns_0(self):
        """NO status maps to integer 0 in the database."""
        from routers.socioeconomico import _mapear_a_db
        assert _mapear_a_db("NO") == 0

    def test_status_to_db_no_aplica_returns_none(self):
        """NO_APLICA status maps to NULL (None) in the database."""
        from routers.socioeconomico import _mapear_a_db
        assert _mapear_a_db("NO_APLICA") is None

    def test_status_to_db_none_returns_none(self):
        """None input maps to None."""
        from routers.socioeconomico import _mapear_a_db
        assert _mapear_a_db(None) is None

    def test_db_to_status_1_returns_si(self):
        """DB value 1 maps to SI string."""
        from routers.socioeconomico import _mapear_de_db
        assert _mapear_de_db(1) == "SI"

    def test_db_to_status_0_returns_no(self):
        """DB value 0 maps to NO string."""
        from routers.socioeconomico import _mapear_de_db
        assert _mapear_de_db(0) == "NO"

    def test_db_to_status_none_returns_none(self):
        """DB NULL remains None so unknown/no aplica is not collapsed to NO."""
        from routers.socioeconomico import _mapear_de_db
        assert _mapear_de_db(None) is None

    def test_status_to_db_unknown_returns_none(self):
        """Unknown status string returns None (safe fallback)."""
        from routers.socioeconomico import _mapear_a_db
        assert _mapear_a_db("INVALIDO") is None


# =============================================================================
# TASK-15: Backward Compatibility Tests (Model Level)
# =============================================================================

class TestBackwardCompatibility:
    """Tests that old boolean payload format is still accepted."""

    def test_tutorin_accepts_new_string_format(self):
        """TutorIn accepts imss_estatus and infonavit_estatus as strings."""
        from routers.socioeconomico import TutorIn

        tutor = TutorIn(
            numero_tutor=1,
            nombre="Test Tutor",
            imss_estatus="SI",
            infonavit_estatus="NO",
        )
        assert tutor.imss_estatus == "SI"
        assert tutor.infonavit_estatus == "NO"

    def test_tutorin_rejects_no_aplica(self):
        """TutorIn rejects NO_APLICA because IMSS/INFONAVIT uses SI/NO or null."""
        from routers.socioeconomico import TutorIn
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TutorIn(
                numero_tutor=1,
                nombre="Test Tutor",
                imss_estatus="NO_APLICA",
                infonavit_estatus="NO_APLICA",
            )

    def test_tutorin_defaults_to_none_when_not_provided(self):
        """TutorIn default values are None for status fields."""
        from routers.socioeconomico import TutorIn

        tutor = TutorIn(numero_tutor=1, nombre="Test Tutor")
        assert tutor.imss_estatus is None
        assert tutor.infonavit_estatus is None

    def test_tutorin_rejects_invalid_status_string(self):
        """TutorIn rejects strings outside the catalog."""
        from routers.socioeconomico import TutorIn
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TutorIn(
                numero_tutor=1,
                nombre="Test Tutor",
                imss_estatus="TAL_VEZ",
            )

    def test_tutorin_accepts_old_boolean_tiene_imss_true(self):
        """TutorIn maps old tiene_imss=True boolean to imss_estatus='SI'."""
        from routers.socioeconomico import TutorIn

        tutor = TutorIn(
            numero_tutor=1,
            nombre="Test Tutor",
            tiene_imss=True,
        )
        assert tutor.imss_estatus == "SI"

    def test_tutorin_accepts_old_boolean_tiene_imss_false(self):
        """TutorIn maps old tiene_imss=False boolean to imss_estatus='NO'."""
        from routers.socioeconomico import TutorIn

        tutor = TutorIn(
            numero_tutor=1,
            nombre="Test Tutor",
            tiene_imss=False,
        )
        assert tutor.imss_estatus == "NO"

    def test_tutorin_accepts_old_boolean_tiene_infonavit(self):
        """TutorIn maps old tiene_infonavit boolean to infonavit_estatus."""
        from routers.socioeconomico import TutorIn

        tutor = TutorIn(
            numero_tutor=1,
            nombre="Test Tutor",
            tiene_infonavit=True,
        )
        assert tutor.infonavit_estatus == "SI"

    def test_new_format_takes_precedence_over_old(self):
        """When both new and old fields are provided, new format wins."""
        from routers.socioeconomico import TutorIn

        tutor = TutorIn(
            numero_tutor=1,
            nombre="Test Tutor",
            imss_estatus="NO",
            tiene_imss=True,  # should be ignored since imss_estatus is provided
        )
        assert tutor.imss_estatus == "NO"


# =============================================================================
# TASK-16: Integration Tests (Full API Flow)
# =============================================================================

class TestIMSSINFONAVITIntegration:
    """Integration tests for the full IMSS/INFONAVIT triestado flow via HTTP."""

    def _triestado_payload(self, region_id: int) -> dict:
        """Base payload with new triestado format."""
        return {
            "region_id": region_id,
            "sede": "Sede Test Triestado",
            "ciudad_registro": "LEON, GTO",
            "beneficiario": {
                "nombres": "BENEFICIARIO",
                "apellido_paterno": "TRIESTADO",
                "apellido_materno": "TEST",
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
                    "nombre": "Tutor Triestado",
                    "imss_estatus": "SI",
                    "infonavit_estatus": "NO",
                }
            ],
            "estudio": {
                "tuvo_silla_previa": False,
                "fecha_estudio": "2026-05-05",
                "status": "borrador",
            },
        }

    # --- POST (new format) ---

    def test_post_estudio_with_new_triestado_format(self, client, capturista_headers, region_lon):
        """POST /estudios accepts imss_estatus and infonavit_estatus strings."""
        payload = self._triestado_payload(region_lon["id"])
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201
        data = res.json()
        assert "estudio_id" in data

    def test_post_estudio_with_boolean_status_values(self, client, capturista_headers, region_lon):
        """POST accepts SI/NO for both fields."""
        payload = self._triestado_payload(region_lon["id"])
        payload["tutores"][0]["imss_estatus"] = "SI"
        payload["tutores"][0]["infonavit_estatus"] = "NO"

        # Add a second tutor with different states
        payload["tutores"].append({
            "numero_tutor": 2,
            "nombre": "Tutor 2 Triestado",
            "imss_estatus": "NO",
            "infonavit_estatus": "SI",
        })

        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201

    # --- GET (returns new format) ---

    def test_get_estudio_returns_triestado_strings(self, client, capturista_headers, region_lon):
        """GET /estudios/{id} returns imss_estatus and infonavit_estatus as strings."""
        payload = self._triestado_payload(region_lon["id"])
        payload["tutores"][0]["imss_estatus"] = "SI"
        payload["tutores"][0]["infonavit_estatus"] = "NO"

        create_res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_res.status_code == 201
        estudio_id = create_res.json()["estudio_id"]

        get_res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_res.status_code == 200
        data = get_res.json()
        tutor = data["tutores"][0]

        assert tutor["imss_estatus"] == "SI"
        assert tutor["infonavit_estatus"] == "NO"
        # Verify old keys are NOT present
        assert "tiene_imss" not in tutor
        assert "tiene_infonavit" not in tutor

    def test_get_estudio_returns_null_for_nulls(self, client, capturista_headers, region_lon):
        """GET preserves NULL when DB columns are not provided."""
        payload = self._triestado_payload(region_lon["id"])
        # Don't set imss_estatus or infonavit_estatus at all (default None → DB NULL)
        del payload["tutores"][0]["imss_estatus"]
        del payload["tutores"][0]["infonavit_estatus"]

        create_res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_res.status_code == 201
        estudio_id = create_res.json()["estudio_id"]

        get_res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_res.status_code == 200
        tutor = get_res.json()["tutores"][0]

        # NULL in DB remains null in the response.
        assert tutor["imss_estatus"] is None
        assert tutor["infonavit_estatus"] is None

    # --- POST (old backward compatible format) ---

    def test_post_estudio_with_old_boolean_format(self, client, capturista_headers, region_lon):
        """POST /estudios still accepts old tiene_imss boolean format during transition."""
        payload = self._triestado_payload(region_lon["id"])
        del payload["tutores"][0]["imss_estatus"]
        del payload["tutores"][0]["infonavit_estatus"]
        payload["tutores"][0]["tiene_imss"] = True
        payload["tutores"][0]["tiene_infonavit"] = False

        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201

        # Verify it returns the new format
        estudio_id = res.json()["estudio_id"]
        get_res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_res.status_code == 200
        tutor = get_res.json()["tutores"][0]
        assert tutor["imss_estatus"] == "SI"
        assert tutor["infonavit_estatus"] == "NO"

    # --- PATCH ---

    def test_patch_estudio_with_triestado_format(self, client, capturista_headers, region_lon):
        """PATCH /estudios/{id} accepts and persists triestado strings."""
        payload = self._triestado_payload(region_lon["id"])
        payload["tutores"][0]["imss_estatus"] = "SI"
        payload["tutores"][0]["infonavit_estatus"] = "NO"

        create_res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_res.status_code == 201
        estudio_id = create_res.json()["estudio_id"]

        # PATCH to change states
        patch_res = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json={
                "tutores": [
                    {
                        "numero_tutor": 1,
                        "nombre": "Tutor Triestado Updated",
                        "imss_estatus": None,
                        "infonavit_estatus": "SI",
                    }
                ]
            },
        )
        assert patch_res.status_code == 200

        # Verify persisted
        get_res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_res.status_code == 200
        tutor = get_res.json()["tutores"][0]
        assert tutor["imss_estatus"] is None
        assert tutor["infonavit_estatus"] == "SI"
        assert tutor["nombre"] == "TUTOR TRIESTADO UPDATED"  # normalized to uppercase

    # --- Rejection tests ---

    def test_post_rejects_invalid_triestado_value(self, client, capturista_headers, region_lon):
        """POST rejects non-catalog triestado values with 422."""
        payload = self._triestado_payload(region_lon["id"])
        payload["tutores"][0]["imss_estatus"] = "TAL_VEZ"

        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 422

    def test_patch_rejects_invalid_triestado_value(self, client, capturista_headers, region_lon):
        """PATCH rejects non-catalog triestado values with 422."""
        payload = self._triestado_payload(region_lon["id"])
        create_res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_res.status_code == 201
        estudio_id = create_res.json()["estudio_id"]

        patch_res = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json={
                "tutores": [
                    {
                        "numero_tutor": 1,
                        "nombre": "Tutor Triestado",
                        "imss_estatus": "INVALIDO",
                    }
                ]
            },
        )
        assert patch_res.status_code == 422

    # --- Completo status flow ---

    def test_post_estudio_completo_with_triestado(self, client, capturista_headers, region_lon):
        """POST estudio completo properly persists triestado values."""
        payload = self._triestado_payload(region_lon["id"])
        payload["estudio"]["status"] = "completo"
        payload["tutores"][0]["imss_estatus"] = None
        payload["tutores"][0]["infonavit_estatus"] = None

        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201

        estudio_id = res.json()["estudio_id"]
        get_res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_res.json()["tutores"][0]["imss_estatus"] is None
        assert get_res.json()["tutores"][0]["infonavit_estatus"] is None


# =============================================================================
# TASK-16 (continued): Database Integrity Tests
# =============================================================================

class TestTriestadoDatabaseIntegrity:
    """Verify raw database values after triestado operations."""

    def test_si_is_persisted_as_1_in_db(self, client, capturista_headers, region_lon):
        """Verify SI is stored as integer 1 in the database."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "Sede DB Test",
            "ciudad_registro": "LEON, GTO",
            "beneficiario": {
                "nombres": "DB",
                "apellido_paterno": "INTEGRITY",
                "apellido_materno": "CHECK",
                "fecha_nacimiento": "2000-01-15",
                "diagnostico": "Test",
                "calle": "Calle 1",
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
                    "nombre": "DB Integrity",
                    "imss_estatus": "SI",
                    "infonavit_estatus": None,
                }
            ],
            "estudio": {
                "tuvo_silla_previa": False,
                "fecha_estudio": "2026-05-05",
                "status": "borrador",
            },
        }
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201

        # Verify via GET response — imss_estatus returns "SI"
        estudio_id = res.json()["estudio_id"]
        get_res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        tutor = get_res.json()["tutores"][0]
        assert tutor["imss_estatus"] == "SI"
        assert tutor["infonavit_estatus"] is None
