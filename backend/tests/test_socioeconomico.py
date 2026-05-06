import pytest


def _estudio_payload(region_id: int) -> dict:
    return {
        "region_id": region_id,
        "sede": "León sede Forum",
        "ciudad_registro": "LEON, GTO",
        "beneficiario": {
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "RBAC",
            "apellido_materno": "TEST",
            "fecha_nacimiento": "2001-01-15",
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
                "nombre": "Tutor RBAC",
                "estado_civil": "CASADO",
                "tiene_imss": True,
                "tiene_infonavit": False,
                "sin_empleo": True,
                "ingreso_mensual": 9999,
                "fuente_empleo": "X",
            }
        ],
        "estudio": {
            "tuvo_silla_previa": False,
            "elaboro_estudio": "Capturista Test",
            "fecha_estudio": "2026-04-19",
            "status": "borrador",
        },
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


class TestSocioeconomicoRbac:
    @pytest.mark.parametrize("telefono", ["4621234567", " 4621234567 "])
    def test_post_estudios_accepts_exactly_10_numeric_phone(
        self,
        client,
        capturista_headers,
        region_lon,
        telefono,
    ):
        payload = _estudio_payload(region_lon["id"])
        payload["beneficiario"]["telefonos"] = telefono

        response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=payload,
        )

        assert response.status_code == 201

    @pytest.mark.parametrize(
        "telefono",
        [
            "123456789",
            "12345678901",
            "12345abcde",
            "12345 6789",
            "12345-6789",
            "",
        ],
    )
    def test_post_estudios_rejects_invalid_phone_format(
        self,
        client,
        capturista_headers,
        region_lon,
        telefono,
    ):
        payload = _estudio_payload(region_lon["id"])
        payload["beneficiario"]["telefonos"] = telefono

        response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=payload,
        )

        assert response.status_code == 422
        assert "El teléfono debe contener exactamente 10 dígitos numéricos" in response.text

    @pytest.mark.parametrize("estado_civil", ["CASADO", "SOLTERO", "VIUDO", "DIVORCIADO", "UNION_LIBRE", "", None])
    def test_post_estudios_accepts_estado_civil_catalog_values(
        self,
        client,
        capturista_headers,
        region_lon,
        estado_civil,
    ):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["estado_civil"] = estado_civil

        response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=payload,
        )

        assert response.status_code == 201

    def test_post_estudios_rejects_invalid_estado_civil_value(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["estado_civil"] = "INVALIDO"

        response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=payload,
        )

        assert response.status_code == 422
        assert "estado_civil" in response.text

    def test_elaboro_estudio_ignored_and_replaced_by_session(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["elaboro_estudio"] = "MANIPULADO"
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]
        data = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers).json()
        assert data["elaboro_estudio"] == "Capturista Test"

    def test_estado_fuera_catalogo_rechazado(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["beneficiario"]["estado_codigo"] = "99"
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 422

    def test_estado_nombre_inconsistente_rechazado(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["beneficiario"]["estado_codigo"] = "11"
        payload["beneficiario"]["estado_nombre"] = "JALISCO"
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 422

    def test_num_hijos_fuera_rango_rechazado(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["num_hijos"] = 31
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 422

    def test_antiguedad_meses_fuera_rango_rechazado(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["antiguedad_meses_extra"] = 12
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 422

    def test_silla_previa_false_nulifica_como_obtuvo(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["tuvo_silla_previa"] = False
        payload["estudio"]["como_obtuvo_silla"] = "Prestada"
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]
        data = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers).json()
        assert data["como_obtuvo_silla"] is None

    def test_edad_17_rechazada(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["edad"] = 17
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 422

    def test_sin_empleo_fuerza_ingreso_cero_y_fuente_null(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["sin_empleo"] = True
        payload["tutores"][0]["ingreso_mensual"] = 1000
        payload["tutores"][0]["fuente_empleo"] = "Empleado"
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]
        data = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers).json()
        assert data["tutores"][0]["ingreso_mensual"] == 0
        assert data["tutores"][0]["fuente_empleo"] is None

    def test_patch_estudios_rejects_invalid_estado_civil_value(self, client, capturista_headers, region_lon):
        create_payload = _estudio_payload(region_lon["id"])
        create_response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=create_payload,
        )
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        patch_payload = {
            "tutores": [
                {
                    "numero_tutor": 1,
                    "nombre": "Tutor RBAC",
                    "estado_civil": "Union libre",
                    "tiene_imss": True,
                    "tiene_infonavit": False,
                }
            ]
        }

        response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json=patch_payload,
        )

        assert response.status_code == 422
        assert "Casado" in response.text
        assert "Soltero" in response.text
        assert "Viudo" in response.text

    def test_patch_estudios_persists_tutor_estado_civil_update(self, client, capturista_headers, region_lon):
        create_payload = _estudio_payload(region_lon["id"])
        create_response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=create_payload,
        )
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        patch_payload = {
            "tutores": [
                {
                    "numero_tutor": 1,
                    "nombre": "Tutor RBAC",
                    "estado_civil": "Soltero",
                    "tiene_imss": True,
                    "tiene_infonavit": False,
                }
            ]
        }

        patch_response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json=patch_payload,
        )
        assert patch_response.status_code == 200

        get_response = client.get(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["tutores"][0]["estado_civil"] == "Soltero"

    def test_tecnico_cannot_create_estudio(self, client, tecnico_headers, region_lon):
        response = client.post(
            "/api/estudios",
            headers=tecnico_headers,
            json=_estudio_payload(region_lon["id"]),
        )
        assert response.status_code == 403

    def test_capturista_owner_can_patch_borrador(self, client, capturista_headers, region_lon):
        create_response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=_estudio_payload(region_lon["id"]),
        )
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        patch_response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json={"status": "completo"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "completo"

    def test_non_owner_capturista_get_and_patch_forbidden(
        self,
        client,
        admin_headers,
        capturista_headers,
        region_lon,
    ):
        create_response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=_estudio_payload(region_lon["id"]),
        )
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        other_capturista_headers = _create_user_and_login(
            client,
            admin_headers,
            suffix="other-cap",
            rol="capturista",
        )

        get_response = client.get(
            f"/api/estudios/{estudio_id}",
            headers=other_capturista_headers,
        )
        assert get_response.status_code == 403

        patch_response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=other_capturista_headers,
            json={"status": "completo"},
        )
        assert patch_response.status_code == 403

    def test_admin_can_get_foreign_estudio(self, client, admin_headers, capturista_headers, region_lon):
        create_response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=_estudio_payload(region_lon["id"]),
        )
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=admin_headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == estudio_id


class TestSocioeconomicoMonetaryContract:
    def test_post_persists_clean_numeric_monetary_fields(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["ingreso_mensual"] = 12500
        payload["tutores"].append(
            {
                "numero_tutor": 2,
                "nombre": "Tutor Secundario",
                "ingreso_mensual": 8400,
                "tiene_imss": False,
                "tiene_infonavit": False,
            }
        )
        payload["estudio"]["monto_otras_fuentes"] = 2500.75

        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        data = get_response.json()

        tutor_by_num = {t["numero_tutor"]: t for t in data["tutores"]}
        assert tutor_by_num[1]["ingreso_mensual"] == 12500
        assert tutor_by_num[2]["ingreso_mensual"] == 8400
        assert data["monto_otras_fuentes"] == 2500.75

    def test_patch_uses_same_numeric_contract_for_monto_otras_fuentes(
        self,
        client,
        capturista_headers,
        region_lon,
    ):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["monto_otras_fuentes"] = 1000.0

        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        patch_response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json={"monto_otras_fuentes": 3499.25, "status": "borrador"},
        )
        assert patch_response.status_code == 200

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        assert get_response.json()["monto_otras_fuentes"] == 3499.25

    def test_post_and_patch_allow_null_for_empty_or_invalidated_monetary_inputs(
        self,
        client,
        capturista_headers,
        region_lon,
    ):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["ingreso_mensual"] = None
        payload["estudio"]["monto_otras_fuentes"] = None

        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["tutores"][0]["ingreso_mensual"] is None
        assert data["monto_otras_fuentes"] is None

        patch_response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json={"monto_otras_fuentes": None, "status": "borrador"},
        )
        assert patch_response.status_code == 200

        get_after_patch = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_after_patch.status_code == 200
        assert get_after_patch.json()["monto_otras_fuentes"] is None

class TestNivelEstudiosCatalog:
    """RF-02: nivel_estudios must use closed 8-code catalog."""

    NIVEL_ESTUDIOS_VALID = [
        "NINGUNO", "PRIMARIA", "SECUNDARIA", "BACHILLERATO",
        "LICENCIATURA", "MAESTRIA", "DOCTORADO", "TECNICO",
    ]

    @pytest.mark.parametrize("codigo", NIVEL_ESTUDIOS_VALID)
    def test_post_accepts_each_valid_catalog_code(self, client, capturista_headers, region_lon, codigo):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["nivel_estudios"] = codigo
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 201, f"Expected 201 for {codigo}, got {response.status_code}: {response.text}"

    def test_post_rejects_invalid_nivel_estudios(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["nivel_estudios"] = "LICENCIATURA_EN_COMPUTACION"
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 422
        assert "nivel_estudios fuera de catálogo" in response.text

    @pytest.mark.parametrize("valor", [None, ""])
    def test_post_accepts_empty_nivel_estudios(self, client, capturista_headers, region_lon, valor):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["nivel_estudios"] = valor
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 201


class TestIngresoMensualInteger:
    """RF-03: ingreso_mensual must be integer 0–9,999,999."""

    def test_post_accepts_integer_max(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["ingreso_mensual"] = 9999999
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 201

    def test_post_accepts_integer_min_zero(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["ingreso_mensual"] = 0
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 201

    def test_post_rejects_negative(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["ingreso_mensual"] = -1
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 422

    def test_post_rejects_overflow(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["ingreso_mensual"] = 10000000
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 422

    def test_post_persists_integer_as_integer(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["ingreso_mensual"] = 12500
        payload["tutores"][0]["sin_empleo"] = False
        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]
        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["tutores"][0]["ingreso_mensual"] == 12500


class TestComoObtuvoSillaCatalog:
    """RF-04: como_obtuvo_silla must be COMPRA or DONACION when tuvo_silla_previa=true."""

    def test_post_accepts_compra_with_silla_previa(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["tuvo_silla_previa"] = True
        payload["estudio"]["como_obtuvo_silla"] = "COMPRA"
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 201
        estudio_id = response.json()["estudio_id"]
        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.json()["como_obtuvo_silla"] == "COMPRA"

    def test_post_accepts_donacion_with_silla_previa(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["tuvo_silla_previa"] = True
        payload["estudio"]["como_obtuvo_silla"] = "DONACION"
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 201

    def test_post_rejects_invalid_como_obtuvo_with_silla_previa(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["tuvo_silla_previa"] = True
        payload["estudio"]["como_obtuvo_silla"] = "REGALO"
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 422
        assert "como_obtuvo_silla no pertenece al catálogo" in response.text

    def test_post_nullifies_como_obtuvo_when_silla_previa_false(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["tuvo_silla_previa"] = False
        payload["estudio"]["como_obtuvo_silla"] = "COMPRA"
        response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert response.status_code == 201
        estudio_id = response.json()["estudio_id"]
        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.json()["como_obtuvo_silla"] is None


class TestSocioeconomicoDocumentContracts:
    def test_post_estudio_persists_document_refs(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"].update(
            {
                "credencial_path": "credencial/doc-1.pdf",
                "credencial_url": "storage://documentos-estudio/credencial/doc-1.pdf",
                "comprobante_domicilio_path": "comprobante_domicilio/doc-2.png",
                "comprobante_domicilio_url": "storage://documentos-estudio/comprobante_domicilio/doc-2.png",
            }
        )

        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["credencial_path"] == "credencial/doc-1.pdf"
        assert data["credencial_url"] == "storage://documentos-estudio/credencial/doc-1.pdf"
        assert data["comprobante_domicilio_path"] == "comprobante_domicilio/doc-2.png"
        assert data["comprobante_domicilio_url"] == "storage://documentos-estudio/comprobante_domicilio/doc-2.png"

    def test_patch_estudio_updates_document_refs(self, client, capturista_headers, region_lon):
        create_response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=_estudio_payload(region_lon["id"]),
        )
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        patch_response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json={
                "credencial_url": "storage://documentos-estudio/credencial/nueva-credencial.pdf",
                "comprobante_domicilio_url": "storage://documentos-estudio/comprobante_domicilio/nuevo-comprobante.jpg",
            },
        )
        assert patch_response.status_code == 200

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["credencial_path"] == "credencial/nueva-credencial.pdf"
        assert data["credencial_url"] == "storage://documentos-estudio/credencial/nueva-credencial.pdf"
        assert data["comprobante_domicilio_path"] == "comprobante_domicilio/nuevo-comprobante.jpg"
        assert data["comprobante_domicilio_url"] == "storage://documentos-estudio/comprobante_domicilio/nuevo-comprobante.jpg"
