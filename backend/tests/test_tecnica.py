def _solicitud_payload(beneficiario_id: int) -> dict:
    return {
        "beneficiario_id": beneficiario_id,
        "entorno": "Urbano / Interiores",
        "control_tronco": "Completo",
        "control_cabeza": "Independiente",
        "control_de_piernas": "Parcial",
        "status": "borrador",
    }


def _create_user_and_login(client, admin_headers: dict, *, suffix: str, rol: str) -> dict:
    email = f"{rol}-{suffix}@test.mx"
    password = f"{rol}-pass-123"
    create_response = client.post(
        "/api/usuarios",
        headers=admin_headers,
        json={
            "nombre": f"{rol.title()} {suffix}",
            "email": email,
            "password": password,
            "rol": rol,
        },
    )
    assert create_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestTecnicaRbac:
    def test_unidad_cm_no_convierte_en_borrador(self, client, tecnico_headers, sample_estudio):
        """Borradores must store measurement values verbatim (no unit conversion).
        Conversion to canonical units (inches/lb) happens only at final submission."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        # status is "borrador" from _solicitud_payload — values must be stored as-is
        payload.update({"unidad_medida": "cm", "altura_total_in": 25.4})
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=tecnico_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_captura"] == "cm"
        # Value must be stored verbatim — NOT converted to 10.0 inches
        assert float(body["altura_total_in"]) == pytest.approx(25.4, rel=1e-3)

    def test_unidad_cm_convierte_al_finalizar(self, client, tecnico_headers, sample_estudio):
        """Unit conversion to canonical (inches/lb) happens only when status becomes completo."""
        medidas_completo = {
            "unidad_medida": "cm",
            "altura_total_in": 25.4,
            "peso_kg": 70.0,
            "medida_cabeza_asiento": 30.0,
            "medida_hombro_asiento": 40.0,
            "medida_prof_asiento": 45.0,
            "medida_rodilla_talon": 35.0,
            "medida_ancho_cadera": 38.0,
            "unidad_peso_captura": "kg",
        }
        payload = {
            "beneficiario_id": sample_estudio["beneficiario_id"],
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "status": "completo",
            **medidas_completo,
        }
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=tecnico_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_captura"] == "cm"
        # 25.4 cm ÷ 2.54 = 10.0 inches — conversion must have happened
        assert float(body["altura_total_in"]) == pytest.approx(10.0, rel=1e-3)

    def test_capturista_cannot_create_solicitud(self, client, capturista_headers, sample_estudio):
        response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert response.status_code == 403

    def test_tecnico_owner_can_patch_borrador(self, client, tecnico_headers, sample_estudio):
        create_response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=tecnico_headers,
            json={"status": "completo", "prioridad": "Alta"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "completo"

    def test_patch_rechaza_unidad_medida_invalida(self, client, tecnico_headers, sample_estudio):
        create_response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=tecnico_headers,
            json={"unidad_medida": "mm"},
        )
        assert patch_response.status_code == 422

    def test_patch_rechaza_medida_fuera_de_rango(self, client, tecnico_headers, sample_estudio):
        create_response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=tecnico_headers,
            json={"peso_kg": -1},
        )
        assert patch_response.status_code == 422

    def test_non_owner_tecnico_patch_forbidden(
        self,
        client,
        admin_headers,
        tecnico_headers,
        sample_estudio,
    ):
        create_response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        other_tecnico_headers = _create_user_and_login(
            client,
            admin_headers,
            suffix="other-tec",
            rol="tecnico",
        )

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=other_tecnico_headers,
            json={"status": "completo"},
        )
        assert patch_response.status_code == 403

    def test_admin_can_patch_foreign_solicitud(
        self,
        client,
        admin_headers,
        tecnico_headers,
        sample_estudio,
    ):
        create_response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=admin_headers,
            json={"status": "completo", "prioridad": "Media"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "completo"

    def test_capturista_cannot_close_existing_solicitud(
        self,
        client,
        capturista_headers,
        tecnico_headers,
        sample_estudio,
    ):
        create_response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        close_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={"status": "completo"},
        )
        assert close_response.status_code == 403


# ---------------------------------------------------------------------------
# Phase 5: Measura validation tests (Pydantic model-level, no DB needed)
# ---------------------------------------------------------------------------

import pytest
from pydantic import ValidationError
from routers.tecnica import SolicitudCreateRequest, SolicitudUpdateRequest


class TestMedidaValidation:
    """Test Pydantic validation of medida fields (tasks 5.1-5.2)."""

    def _base_payload(self):
        return {
            "beneficiario_id": 1,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
        }

    def test_acepta_entero_simple_como_string(self):
        """Valid integer string is accepted and converted to Decimal."""
        payload = self._base_payload()
        payload["altura_total_in"] = "2"
        model = SolicitudCreateRequest(**payload)
        from decimal import Decimal
        assert model.altura_total_in == Decimal("2.000")

    def test_acepta_decimal_tres_digitos(self):
        """Decimal string with 3 places is preserved."""
        payload = self._base_payload()
        payload["medida_cabeza_asiento"] = "2.100"
        model = SolicitudCreateRequest(**payload)
        from decimal import Decimal
        assert model.medida_cabeza_asiento == Decimal("2.100")

    def test_acepta_leading_zeros(self):
        """Leading zeros are normalized."""
        payload = self._base_payload()
        payload["peso_kg"] = "002.3"
        model = SolicitudCreateRequest(**payload)
        from decimal import Decimal
        assert model.peso_kg == Decimal("2.300")

    def test_acepta_valor_grande(self):
        """Value near max (1000.320) passes."""
        payload = self._base_payload()
        payload["altura_total_in"] = "1000.320"
        model = SolicitudCreateRequest(**payload)
        from decimal import Decimal
        assert model.altura_total_in == Decimal("1000.320")

    def test_acepta_valor_maximo(self):
        """Maximum allowed value (9999.999) passes."""
        payload = self._base_payload()
        payload["altura_total_in"] = "9999.999"
        model = SolicitudCreateRequest(**payload)
        from decimal import Decimal
        assert model.altura_total_in == Decimal("9999.999")

    def test_rechaza_mas_de_4_enteros(self):
        """5 integer digits raises ValidationError."""
        payload = self._base_payload()
        payload["altura_total_in"] = "12345"
        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**payload)
        errors = exc_info.value.errors()
        assert any("altura_total_in" in str(e.get("loc", [])) for e in errors)

    def test_rechaza_mas_de_3_decimales(self):
        """4 decimal places raises ValidationError."""
        payload = self._base_payload()
        payload["medida_cabeza_asiento"] = "2.1234"
        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**payload)
        errors = exc_info.value.errors()
        assert any("medida_cabeza_asiento" in str(e.get("loc", [])) for e in errors)

    def test_rechaza_dos_puntos(self):
        """Two decimal points raise ValidationError."""
        payload = self._base_payload()
        payload["altura_total_in"] = "1..2"
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_rechaza_coma(self):
        """Comma as decimal separator raises ValidationError."""
        payload = self._base_payload()
        payload["peso_kg"] = "12,3"
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_rechaza_letras(self):
        """Alphabetic chars raise ValidationError."""
        payload = self._base_payload()
        payload["altura_total_in"] = "abc"
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_rechaza_negativo(self):
        """Negative sign raises ValidationError."""
        payload = self._base_payload()
        payload["peso_kg"] = "-2"
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_null_es_aceptado(self):
        """None/null is accepted (optional field)."""
        payload = self._base_payload()
        payload["altura_total_in"] = None
        model = SolicitudCreateRequest(**payload)
        assert model.altura_total_in is None

    def test_vacio_es_null(self):
        """Empty string is treated as None."""
        payload = self._base_payload()
        payload["altura_total_in"] = ""
        model = SolicitudCreateRequest(**payload)
        assert model.altura_total_in is None

    def test_normalizacion_entero_a_tres_decimales(self):
        """Integer "2" becomes Decimal("2.000")."""
        payload = self._base_payload()
        payload["peso_kg"] = "2"
        model = SolicitudCreateRequest(**payload)
        from decimal import Decimal
        assert model.peso_kg == Decimal("2.000")

    def test_patch_acepta_mismos_validadores(self):
        """SolicitudUpdateRequest applies same validators."""
        payload = {"altura_total_in": "2.5"}
        model = SolicitudUpdateRequest(**payload)
        from decimal import Decimal
        assert model.altura_total_in == Decimal("2.500")

    def test_patch_rechaza_invalido(self):
        """SolicitudUpdateRequest rejects invalid values."""
        with pytest.raises(ValidationError):
            SolicitudUpdateRequest(altura_total_in="abc")


class TestObservacionesPosturalesValidation:
    """Test Pydantic validation of observaciones_posturales (tasks 5.3-5.4)."""

    def _base_payload(self):
        return {
            "beneficiario_id": 1,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
        }

    def test_acepta_texto_valido(self):
        """Valid text with allowed chars passes."""
        payload = self._base_payload()
        payload["observaciones_posturales"] = "Paciente con escoliosis."
        model = SolicitudCreateRequest(**payload)
        assert model.observaciones_posturales == "Paciente con escoliosis."

    def test_acepta_null(self):
        """None is accepted."""
        payload = self._base_payload()
        model = SolicitudCreateRequest(**payload)
        assert model.observaciones_posturales is None

    def test_rechaza_arroba(self):
        """@ symbol raises ValidationError."""
        payload = self._base_payload()
        payload["observaciones_posturales"] = "email@test.com"
        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**payload)
        errors = exc_info.value.errors()
        assert any("observaciones_posturales" in str(e.get("loc", [])) for e in errors)

    def test_rechaza_script_tag(self):
        """HTML tags raise ValidationError."""
        payload = self._base_payload()
        payload["observaciones_posturales"] = "<script>alert(1)</script>"
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_rechaza_excede_500_chars(self):
        """Text exceeding 500 chars raises ValidationError."""
        payload = self._base_payload()
        payload["observaciones_posturales"] = "x" * 501
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_acepta_exactamente_500(self):
        """Exactly 500 allowed chars passes."""
        payload = self._base_payload()
        payload["observaciones_posturales"] = "a" * 500
        model = SolicitudCreateRequest(**payload)
        assert len(model.observaciones_posturales) == 500


class TestValidationErrorFormat:
    """Test that Pydantic validation errors include structured detail (task 5.8)."""

    def _base_payload(self):
        return {
            "beneficiario_id": 1,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
        }

    def test_error_tiene_loc_field(self):
        """Validation errors include field location (loc)."""
        payload = self._base_payload()
        payload["altura_total_in"] = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**payload)
        errors = exc_info.value.errors()
        assert len(errors) >= 1
        # Pydantic v2 error format: loc is a tuple, first element is field name
        first_error = errors[0]
        assert "loc" in first_error
        assert "altura_total_in" in str(first_error["loc"])

    def test_error_tiene_msg(self):
        """Validation errors include a message (msg)."""
        payload = self._base_payload()
        payload["altura_total_in"] = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**payload)
        errors = exc_info.value.errors()
        first_error = errors[0]
        assert "msg" in first_error
        assert len(first_error["msg"]) > 0

    def test_error_tiene_type(self):
        """Validation errors include an error type."""
        payload = self._base_payload()
        payload["altura_total_in"] = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**payload)
        errors = exc_info.value.errors()
        first_error = errors[0]
        assert "type" in first_error


# ---------------------------------------------------------------------------
# Weight unit conversion tests (unidades-peso-zoom-imagen)
# ---------------------------------------------------------------------------

class TestWeightUnitConversion:
    """Test lb→kg conversion and unidad_peso_captura validation."""

    def test_post_lb_convierte_a_kg(self, client, tecnico_headers, sample_estudio):
        """POST with unidad_peso_captura=lb converts 220.462 lb → 100.000 kg."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload.update({
            "unidad_peso_captura": "lb",
            "peso_kg": "220.462",
        })
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=tecnico_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_peso_captura"] == "lb"
        assert body["peso_kg"] == 100.0

    def test_post_kg_no_conversion(self, client, tecnico_headers, sample_estudio):
        """POST with unidad_peso_captura=kg stores weight unchanged."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload.update({
            "unidad_peso_captura": "kg",
            "peso_kg": "100.000",
        })
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=tecnico_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["peso_kg"] == 100.0

    def test_patch_lb_convierte_a_kg(self, client, tecnico_headers, sample_estudio):
        """PATCH with unidad_peso_captura=lb + peso_kg converts before storing."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=tecnico_headers,
            json={
                "unidad_peso_captura": "lb",
                "peso_kg": "220.462",
            },
        )
        assert patch_response.status_code == 200
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=tecnico_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_peso_captura"] == "lb"
        assert body["peso_kg"] == 100.0

    def test_rechaza_unidad_peso_invalida(self, client, tecnico_headers, sample_estudio):
        """POST with invalid unidad_peso_captura returns 422."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload["unidad_peso_captura"] = "stone"
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 422

    def test_patch_rechaza_unidad_peso_invalida(self, client, tecnico_headers, sample_estudio):
        """PATCH with invalid unidad_peso_captura returns 422."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=tecnico_headers,
            json={"unidad_peso_captura": "oz"},
        )
        assert patch_response.status_code == 422

    def test_post_default_unidad_peso(self, client, tecnico_headers, sample_estudio):
        """POST without unidad_peso_captura defaults to kg."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload["peso_kg"] = "75.000"
        create_response = client.post("/api/solicitudes", headers=tecnico_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=tecnico_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_peso_captura"] == "kg"
        assert body["peso_kg"] == 75.0
