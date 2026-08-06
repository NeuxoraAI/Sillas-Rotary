def _solicitud_payload(beneficiario_id: int) -> dict:
    return {
        "beneficiario_id": beneficiario_id,
        "entorno": "Urbano / Interiores",
        "control_tronco": "Completo",
        "control_cabeza": "Independiente",
        "control_de_piernas": "Parcial",
        "status": "borrador",
    }


def _medidas_payload() -> dict:
    """Las 7 medidas técnicas obligatorias para cerrar (status="completo").

    Se persisten en el borrador para poder verificar que el cierre por PATCH con
    cuerpo parcial (`{"status": "completo"}`) usa el estado FUSIONADO
    (cuerpo + BD) y no exige reenviarlas (Issue #129).
    """
    return {
        "altura_total_in": "30.0",
        "peso_kg": "20.0",
        "medida_cabeza_asiento": "25.0",
        "medida_hombro_asiento": "18.0",
        "medida_prof_asiento": "16.0",
        "medida_rodilla_talon": "14.0",
        "medida_ancho_cadera": "15.0",
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
    def test_equipo_solicitado_persiste(self, client, capturista_headers, sample_estudio):
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload["equipo_solicitado"] = "Silla de ruedas neurológica PCI"

        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201, create_response.text
        solicitud_id = create_response.json()["solicitud_id"]

        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200, get_response.text
        assert get_response.json()["equipo_solicitado"] == "Silla de ruedas neurológica PCI"

    def test_soporte_oxigeno_persiste(self, client, capturista_headers, sample_estudio):
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload["soporte_oxigeno"] = True
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        assert get_response.json()["soporte_oxigeno"] is True

    def test_unidad_cm_no_convierte_en_borrador(self, client, capturista_headers, sample_estudio):
        """Borradores must store measurement values verbatim (no unit conversion).
        Conversion to canonical units (inches/lb) happens only at final submission."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        # status is "borrador" from _solicitud_payload — values must be stored as-is
        payload.update({"unidad_medida": "cm", "altura_total_in": 25.4})
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_captura"] == "cm"
        # Value must be stored verbatim — NOT converted to 10.0 inches
        assert float(body["altura_total_in"]) == pytest.approx(25.4, rel=1e-3)

    def test_unidad_cm_convierte_al_finalizar(self, client, capturista_headers, sample_estudio):
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
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_captura"] == "cm"
        # 25.4 cm ÷ 2.54 = 10.0 inches — conversion must have happened
        assert float(body["altura_total_in"]) == pytest.approx(10.0, rel=1e-3)

    def test_capturista_can_create_solicitud(self, client, capturista_headers, sample_estudio):
        # Issue #130: el capturista (no el técnico) crea las solicitudes técnicas.
        response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert response.status_code == 201

    def test_tecnico_cannot_create_solicitud(self, client, tecnico_headers, sample_estudio):
        # Issue #130: el técnico es de solo lectura sobre registros → 403 al crear.
        response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert response.status_code == 403

    def test_capturista_owner_can_patch_borrador(self, client, capturista_headers, sample_estudio):
        # Issue #129 + #130: el capturista dueño cierra el borrador con cuerpo
        # PARCIAL (las 7 medidas ya están persistidas) y debe devolver 200.
        payload = {
            **_solicitud_payload(sample_estudio["beneficiario_id"]),
            **_medidas_payload(),
        }
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=payload,
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={"status": "completo", "prioridad": "Alta"},
        )
        assert patch_response.status_code == 200, patch_response.text
        assert patch_response.json()["status"] == "completo"

    def test_close_missing_medidas_returns_422(self, client, capturista_headers, sample_estudio):
        # Issue #129: si faltan medidas en el estado FUSIONADO (cuerpo + BD),
        # el cierre por PATCH parcial devuelve 422 con el detalle de faltantes.
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={"status": "completo"},
        )
        assert patch_response.status_code == 422
        assert "altura_total_in" in patch_response.text

    def test_patch_rechaza_unidad_medida_invalida(self, client, capturista_headers, sample_estudio):
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={"unidad_medida": "mm"},
        )
        assert patch_response.status_code == 422

    def test_patch_rechaza_medida_fuera_de_rango(self, client, capturista_headers, sample_estudio):
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={"peso_kg": -1},
        )
        assert patch_response.status_code == 422

    def test_tecnico_cannot_patch_solicitud(
        self,
        client,
        capturista_headers,
        tecnico_headers,
        sample_estudio,
    ):
        # Issue #130: el técnico → 403 al editar (compuerta de rol, antes de la
        # verificación de titularidad).
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=tecnico_headers,
            json={"status": "completo"},
        )
        assert patch_response.status_code == 403

    def test_non_owner_capturista_patch_forbidden(
        self,
        client,
        admin_headers,
        capturista_headers,
        sample_estudio,
    ):
        # Titularidad: otro capturista (no dueño) no puede editar la solicitud
        # ajena → 403 (assert_resource_owner), aunque su rol sí permita escribir.
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        other_capturista_headers = _create_user_and_login(
            client,
            admin_headers,
            suffix="other-cap",
            rol="capturista",
        )

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=other_capturista_headers,
            json={"status": "completo"},
        )
        assert patch_response.status_code == 403

    def test_admin_can_edit_foreign_solicitud_via_admin_route(
        self,
        client,
        admin_headers,
        capturista_headers,
        sample_estudio,
    ):
        # Issue #130: el admin NO edita por PATCH /solicitudes/{id} (403); usa su
        # ruta dedicada /admin/beneficiarios/{id}/solicitud para campos no-status.
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        # El endpoint de captura queda cerrado al admin.
        forbidden = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=admin_headers,
            json={"prioridad": "Media"},
        )
        assert forbidden.status_code == 403

        # La ruta dedicada del admin edita la solicitud existente → 200.
        admin_edit = client.patch(
            f"/api/admin/beneficiarios/{sample_estudio['beneficiario_id']}/solicitud",
            headers=admin_headers,
            json={"prioridad": "Media"},
        )
        assert admin_edit.status_code == 200, admin_edit.text

    def test_org_leader_can_read_solicitud(
        self,
        client,
        admin_headers,
        capturista_user,
        capturista_headers,
        organizacion_user,
        organizacion_headers,
        sample_estudio,
    ):
        """Regression #54 + #130: el capturista crea/posee la solicitud; el líder
        de la organización que la capturó debe poder leerla vía el bypass de
        líder (assert_resource_owner con db). Un ajeno (sin bypass de admin,
        dueño, líder de org, ni técnico) recibe 403."""
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201, create_response.text
        solicitud_id = create_response.json()["solicitud_id"]

        # Link the org to the capturing account so org-owned solicitudes match
        # the leader-bypass query (organizaciones.usuario_id == solicitud.usuario_id).
        org_response = client.post(
            "/api/organizaciones",
            headers=admin_headers,
            json={"nombre": "Rotary Líder Test", "usuario_id": capturista_user["id"]},
        )
        assert org_response.status_code == 201, org_response.text
        org_id = org_response.json()["id"]

        # A different user (organizacion_user) is the registered leader.
        leader_assign = client.post(
            f"/api/organizaciones/{org_id}/lider",
            headers=admin_headers,
            json={"lider_usuario_id": organizacion_user["id"]},
        )
        assert leader_assign.status_code == 200

        # Leader bypass: organizacion_user leads the org that owns the solicitud → 200
        leader_response = client.get(
            f"/api/solicitudes/{solicitud_id}",
            headers=organizacion_headers,
        )
        assert leader_response.status_code == 200

        # Boundary: an unrelated capturista (not owner, not leader, not admin,
        # not técnico) → 403. Técnico is intentionally excluded from this
        # boundary check — see test_tecnico_can_read_any_solicitud_unrestricted
        # below, which asserts the opposite (técnico is admin-equivalent).
        outsider_headers = _create_user_and_login(
            client, admin_headers, suffix="outsider", rol="capturista"
        )
        outsider_response = client.get(
            f"/api/solicitudes/{solicitud_id}",
            headers=outsider_headers,
        )
        assert outsider_response.status_code == 403

    def test_tecnico_can_read_any_solicitud_unrestricted(
        self, client, admin_headers, capturista_headers, sample_estudio,
    ):
        """Técnico is a read-only, admin-equivalent role (business rule):
        it must be able to read ANY solicitud, including ones it neither
        owns nor leads — assert_resource_owner bypasses técnico the same
        way it bypasses admin."""
        create_response = client.post(
            "/api/solicitudes",
            headers=capturista_headers,
            json=_solicitud_payload(sample_estudio["beneficiario_id"]),
        )
        assert create_response.status_code == 201, create_response.text
        solicitud_id = create_response.json()["solicitud_id"]

        tecnico_headers = _create_user_and_login(
            client, admin_headers, suffix="reader", rol="tecnico"
        )
        response = client.get(
            f"/api/solicitudes/{solicitud_id}",
            headers=tecnico_headers,
        )
        assert response.status_code == 200, response.text


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
            "control_de_piernas": "Parcial",
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
    """Test Pydantic validation of padecimiento (tasks 5.3-5.4)."""

    def _base_payload(self):
        return {
            "beneficiario_id": 1,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
        }

    def test_acepta_texto_valido(self):
        """Valid text with allowed chars passes."""
        payload = self._base_payload()
        payload["padecimiento"] = "Paciente con escoliosis."
        model = SolicitudCreateRequest(**payload)
        # Input is auto-uppercased to align with the backend catalog charset
        assert model.padecimiento == "PACIENTE CON ESCOLIOSIS."

    def test_acepta_null(self):
        """None is accepted."""
        payload = self._base_payload()
        model = SolicitudCreateRequest(**payload)
        assert model.padecimiento is None

    def test_rechaza_arroba(self):
        """@ symbol raises ValidationError."""
        payload = self._base_payload()
        payload["padecimiento"] = "email@test.com"
        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**payload)
        errors = exc_info.value.errors()
        assert any("padecimiento" in str(e.get("loc", [])) for e in errors)

    def test_rechaza_script_tag(self):
        """HTML tags raise ValidationError."""
        payload = self._base_payload()
        payload["padecimiento"] = "<script>alert(1)</script>"
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_rechaza_excede_500_chars(self):
        """Text exceeding 500 chars raises ValidationError."""
        payload = self._base_payload()
        payload["padecimiento"] = "x" * 501
        with pytest.raises(ValidationError):
            SolicitudCreateRequest(**payload)

    def test_acepta_exactamente_500(self):
        """Exactly 500 allowed chars passes."""
        payload = self._base_payload()
        payload["padecimiento"] = "a" * 500
        model = SolicitudCreateRequest(**payload)
        assert len(model.padecimiento) == 500


class TestValidationErrorFormat:
    """Test that Pydantic validation errors include structured detail (task 5.8)."""

    def _base_payload(self):
        return {
            "beneficiario_id": 1,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
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

    def test_post_lb_borrador_stores_verbatim(self, client, capturista_headers, sample_estudio):
        """POST borrador with unidad_peso_captura=lb stores value verbatim (no conversion).
        Conversion to canonical lb happens only at final submission (status=completo)."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload.update({
            "unidad_peso_captura": "lb",
            "peso_kg": "220.462",
        })
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_peso_captura"] == "lb"
        # Borrador: value must be stored as-is, NOT converted
        assert float(body["peso_kg"]) == pytest.approx(220.462, rel=1e-3)

    def test_post_kg_no_conversion(self, client, capturista_headers, sample_estudio):
        """POST with unidad_peso_captura=kg stores weight unchanged."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload.update({
            "unidad_peso_captura": "kg",
            "peso_kg": "100.000",
        })
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["peso_kg"] == 100.0

    def test_patch_lb_borrador_stores_verbatim(self, client, capturista_headers, sample_estudio):
        """PATCH borrador with unidad_peso_captura=lb stores value verbatim (no conversion).
        Conversion only happens when the solicitud is finalized (status=completo)."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={
                "unidad_peso_captura": "lb",
                "peso_kg": "220.462",
                "status": "borrador",
            },
        )
        assert patch_response.status_code == 200
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_peso_captura"] == "lb"
        # Borrador: value must be stored as-is, NOT converted
        assert float(body["peso_kg"]) == pytest.approx(220.462, rel=1e-3)

    def test_rechaza_unidad_peso_invalida(self, client, capturista_headers, sample_estudio):
        """POST with invalid unidad_peso_captura returns 422."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload["unidad_peso_captura"] = "stone"
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 422

    def test_patch_rechaza_unidad_peso_invalida(self, client, capturista_headers, sample_estudio):
        """PATCH with invalid unidad_peso_captura returns 422."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={"unidad_peso_captura": "oz"},
        )
        assert patch_response.status_code == 422

    def test_post_default_unidad_peso(self, client, capturista_headers, sample_estudio):
        """POST without unidad_peso_captura defaults to kg."""
        payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        payload["peso_kg"] = "75.000"
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["unidad_peso_captura"] == "kg"
        assert body["peso_kg"] == 75.0

    def test_patch_finalizar_sin_unidad_medida_convierte_stored_cm(
        self, client, capturista_headers, sample_estudio
    ):
        """PATCH status=completo with measurements but without unidad_medida uses stored capture unit.

        Scenario: borrador was created in cm/kg. El capturista finalizes via PATCH resending the same
        numeric values but omitting unidad_medida — the stored unidad_captura ("cm") must drive
        the conversion, so values end up in canonical inches/lb.
        """
        # 1. Create borrador with cm measurements and kg weight
        borrador_payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        borrador_payload.update({
            "unidad_medida": "cm",
            "unidad_peso_captura": "kg",
            "altura_total_in": 25.4,
            "peso_kg": 100.0,
            "medida_cabeza_asiento": 30.0,
            "medida_hombro_asiento": 40.0,
            "medida_prof_asiento": 45.0,
            "medida_rodilla_talon": 35.0,
            "medida_ancho_cadera": 38.0,
        })
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=borrador_payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        # 2. Finalize: resend same numeric values but omit unidad_medida.
        #    The backend must use stored unidad_captura ("cm") to convert.
        patch_response = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={
                "status": "completo",
                # No unidad_medida → stored "cm" should be used
                "altura_total_in": 25.4,
                "peso_kg": 100.0,
                "medida_cabeza_asiento": 30.0,
                "medida_hombro_asiento": 40.0,
                "medida_prof_asiento": 45.0,
                "medida_rodilla_talon": 35.0,
                "medida_ancho_cadera": 38.0,
            },
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "completo"

        # 3. GET and verify canonical values
        get_response = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        body = get_response.json()

        # unidad_captura must remain as capture audit trail
        assert body["unidad_captura"] == "cm"
        assert body["unidad_peso_captura"] == "kg"

        # Measurements must now be in canonical inches/lb
        assert float(body["altura_total_in"]) == pytest.approx(10.0, rel=1e-3)      # 25.4 cm ÷ 2.54
        assert float(body["peso_kg"]) == pytest.approx(220.462, rel=1e-3)           # 100 kg × 2.20462
        assert float(body["medida_cabeza_asiento"]) == pytest.approx(11.811, rel=1e-3)  # 30 cm ÷ 2.54

    def test_patch_completo_dos_veces_no_reconvierte(
        self, client, capturista_headers, sample_estudio
    ):
        """Idempotency guard: a second PATCH with status=completo (and no
        unidad_medida) on an already-completo solicitud must NOT re-convert
        values that are already canonical — unidad_captura stays "cm"
        forever as an audit trail, so the conversion branch must key off
        the solicitud's own status, not that field."""
        borrador_payload = _solicitud_payload(sample_estudio["beneficiario_id"])
        borrador_payload.update({
            "unidad_medida": "cm",
            "unidad_peso_captura": "kg",
            "altura_total_in": 25.4,
            "peso_kg": 100.0,
            "medida_cabeza_asiento": 30.0,
            "medida_hombro_asiento": 40.0,
            "medida_prof_asiento": 45.0,
            "medida_rodilla_talon": 35.0,
            "medida_ancho_cadera": 38.0,
        })
        create_response = client.post("/api/solicitudes", headers=capturista_headers, json=borrador_payload)
        assert create_response.status_code == 201
        solicitud_id = create_response.json()["solicitud_id"]

        finalize_body = {
            "status": "completo",
            "altura_total_in": 25.4,
            "peso_kg": 100.0,
            "medida_cabeza_asiento": 30.0,
            "medida_hombro_asiento": 40.0,
            "medida_prof_asiento": 45.0,
            "medida_rodilla_talon": 35.0,
            "medida_ancho_cadera": 38.0,
        }

        first = client.patch(
            f"/api/solicitudes/{solicitud_id}", headers=capturista_headers, json=finalize_body,
        )
        assert first.status_code == 200

        first_get = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        first_body = first_get.json()
        assert float(first_body["altura_total_in"]) == pytest.approx(10.0, rel=1e-3)

        # Repeat call: no unidad_medida in body, solicitud already "completo".
        second = client.patch(
            f"/api/solicitudes/{solicitud_id}",
            headers=capturista_headers,
            json={"status": "completo"},
        )
        assert second.status_code == 200

        second_get = client.get(f"/api/solicitudes/{solicitud_id}", headers=capturista_headers)
        second_body = second_get.json()

        # Values must be unchanged — NOT divided/multiplied a second time.
        assert float(second_body["altura_total_in"]) == pytest.approx(10.0, rel=1e-3)
        assert float(second_body["peso_kg"]) == pytest.approx(220.462, rel=1e-3)
        assert float(second_body["medida_cabeza_asiento"]) == pytest.approx(11.811, rel=1e-3)
