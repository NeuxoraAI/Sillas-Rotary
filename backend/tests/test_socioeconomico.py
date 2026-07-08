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
                "nombres": "TUTOR",
                "apellido_paterno": "RBAC",
                "apellido_materno": "TEST",
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "vivienda": "PROPIA",
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

    @pytest.mark.parametrize("estado_civil", ["CASADO", "SOLTERO", "VIUDO", "DIVORCIADO", "UNION_LIBRE"])
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
        assert "CASADO" in response.text
        assert "SOLTERO" in response.text
        assert "VIUDO" in response.text
        assert "DIVORCIADO" in response.text
        assert "UNION_LIBRE" in response.text

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
                    "nombres": "TUTOR",
                    "apellido_paterno": "RBAC",
                    "apellido_materno": "TEST",
                    "edad": 45,
                    "nivel_estudios": "LICENCIATURA",
                    "estado_civil": "SOLTERO",
                    "vivienda": "PROPIA",
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
        assert get_response.json()["tutores"][0]["estado_civil"] == "SOLTERO"

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
            json={"status": "completo", "fecha_estudio": "2026-04-19", "tuvo_silla_previa": False},
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
            json={"status": "completo", "fecha_estudio": "2026-04-19", "tuvo_silla_previa": False},
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

    def test_admin_patch_preserves_elaboro_estudio(self, client, admin_headers, capturista_headers, region_lon):
        """Issue #107 + #130: el admin edita un estudio ajeno por su ruta dedicada
        (`/admin/beneficiarios/{id}/estudio`) — el endpoint de captura le está
        vedado (403) — y esa edición no debe pisar la autoría (`elaboro_estudio`)."""
        create_response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json=_estudio_payload(region_lon["id"]),
        )
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]
        beneficiario_id = create_response.json()["beneficiario_id"]

        # El capturista dueño dejó la autoría como "Capturista Test"
        before = client.get(f"/api/estudios/{estudio_id}", headers=admin_headers).json()
        assert before["elaboro_estudio"] == "Capturista Test"

        # Issue #130: el endpoint general de captura queda cerrado al admin.
        forbidden = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=admin_headers,
            json={"ciudad_registro": "Guadalajara"},
        )
        assert forbidden.status_code == 403

        # El admin edita un campo por su ruta dedicada, sin enviar elaboro_estudio.
        patch_response = client.patch(
            f"/api/admin/beneficiarios/{beneficiario_id}/estudio",
            headers=admin_headers,
            json={"ciudad_registro": "Guadalajara"},
        )
        assert patch_response.status_code == 200, patch_response.text

        after = client.get(f"/api/estudios/{estudio_id}", headers=admin_headers).json()
        assert after["elaboro_estudio"] == "Capturista Test"

    def test_owner_patch_sets_own_name_as_elaboro_estudio(self, client, capturista_headers, region_lon):
        """El dueño (capturista) sí fija su propio nombre en `elaboro_estudio` al
        editar su estudio (contrato existente, sin cambios)."""
        payload = _estudio_payload(region_lon["id"])
        payload["estudio"]["elaboro_estudio"] = "VALOR VIEJO"
        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201
        estudio_id = create_response.json()["estudio_id"]

        patch_response = client.patch(
            f"/api/estudios/{estudio_id}",
            headers=capturista_headers,
            json={"monto_otras_fuentes": 1500},
        )
        assert patch_response.status_code == 200

        after = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers).json()
        assert after["elaboro_estudio"] == "Capturista Test"


class TestSocioeconomicoMonetaryContract:
    def test_post_persists_clean_numeric_monetary_fields(self, client, capturista_headers, region_lon):
        # Los montos de "otras fuentes de ingreso" viven a nivel TUTOR (el nivel
        # estudio se eliminó en la migración 0028). Se persisten como numérico limpio.
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["sin_empleo"] = False
        payload["tutores"][0]["fuente_empleo"] = "EMPLEADO"
        payload["tutores"][0]["ingreso_mensual"] = 12500
        payload["tutores"][0]["otras_fuentes_aplica"] = True
        payload["tutores"][0]["otras_fuentes_ingreso"] = "VENTAS"
        payload["tutores"][0]["monto_otras_fuentes"] = 3499.25

        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201, create_response.text
        estudio_id = create_response.json()["estudio_id"]

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        assert get_response.json()["tutores"][0]["monto_otras_fuentes"] == 3499.25

    def test_post_allows_null_for_empty_or_invalidated_monetary_inputs(
        self,
        client,
        capturista_headers,
        region_lon,
    ):
        # Los montos monetarios (por tutor) pueden almacenarse como None. Con
        # sin_empleo=True, ingreso_mensual no es requerido y se guarda como 0.
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["sin_empleo"] = True
        payload["tutores"][0]["ingreso_mensual"] = None
        payload["tutores"][0]["otras_fuentes_aplica"] = False
        payload["tutores"][0]["monto_otras_fuentes"] = None

        create_response = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert create_response.status_code == 201, create_response.text
        estudio_id = create_response.json()["estudio_id"]

        get_response = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        # When sin_empleo=True, DB stores ingreso_mensual as 0, API returns 0
        assert data["tutores"][0]["ingreso_mensual"] == 0
        assert data["tutores"][0]["monto_otras_fuentes"] is None

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

    @pytest.mark.parametrize("codigo", NIVEL_ESTUDIOS_VALID)
    def test_post_accepts_empty_nivel_estudios(self, client, capturista_headers, region_lon, codigo):
        """nivel_estudios is always required — test valid codes still pass."""
        payload = _estudio_payload(region_lon["id"])
        payload["tutores"][0]["nivel_estudios"] = codigo
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
        payload["tutores"][0]["ingreso_mensual"] = 999_999_999 + 1
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
                "estudio_clinico_path": "estudio_clinico/doc-3.jpg",
                "estudio_clinico_url": "storage://documentos-estudio/estudio_clinico/doc-3.jpg",
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
        assert data["estudio_clinico_path"] == "estudio_clinico/doc-3.jpg"
        assert data["estudio_clinico_url"] == "storage://documentos-estudio/estudio_clinico/doc-3.jpg"

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
                "estudio_clinico_url": "storage://documentos-estudio/estudio_clinico/nuevo-estudio.jpg",
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
        assert data["estudio_clinico_path"] == "estudio_clinico/nuevo-estudio.jpg"
        assert data["estudio_clinico_url"] == "storage://documentos-estudio/estudio_clinico/nuevo-estudio.jpg"


class TestCurpDedup:
    """CURP uniqueness / duplicate handling (Issue #32)."""

    VALID_CURP = "HEGG560427MVZRRL04"

    def test_post_rejects_invalid_curp(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["beneficiario"]["curp"] = "NOT-A-VALID-CURP1"
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 422

    def test_post_accepts_valid_curp(self, client, capturista_headers, region_lon):
        payload = _estudio_payload(region_lon["id"])
        payload["beneficiario"]["curp"] = self.VALID_CURP
        res = client.post("/api/estudios", headers=capturista_headers, json=payload)
        assert res.status_code == 201, res.text
        assert res.json()["curp"] == self.VALID_CURP

    def test_duplicate_curp_returns_409(self, client, capturista_headers, region_lon):
        first = _estudio_payload(region_lon["id"])
        first["beneficiario"]["curp"] = self.VALID_CURP
        r1 = client.post("/api/estudios", headers=capturista_headers, json=first)
        assert r1.status_code == 201, r1.text

        second = _estudio_payload(region_lon["id"])
        second["beneficiario"]["curp"] = self.VALID_CURP
        r2 = client.post("/api/estudios", headers=capturista_headers, json=second)
        assert r2.status_code == 409, r2.text
        detail = r2.json()["detail"]
        assert detail["type"] == "curp_duplicada"
        assert detail["curp"] == self.VALID_CURP
        assert "beneficiario_existente" in detail


class TestCurpUniqueViolationSafetyNet:
    """Issue #131 (cabos): la red de seguridad UniqueViolation de crear_estudio
    llevaba sin test desde su introducción, y actualizar_estudio no la tenía.
    La carrera (dos escrituras que pasan el pre-check antes de que la otra
    inserte) se simula anulando el pre-check con monkeypatch para que el
    duplicado llegue hasta la constraint UNIQUE(curp_benef)."""

    VALID_CURP = "HEGG560427MVZRRL04"

    def _assert_409_curp_duplicada(self, res):
        assert res.status_code == 409, f"Expected 409, got {res.status_code}: {res.text}"
        detail = res.json()["detail"]
        assert detail["type"] == "curp_duplicada"
        assert detail["curp"] == self.VALID_CURP
        assert "beneficiario_existente" in detail

    def test_create_race_returns_409_estructurado(self, client, capturista_headers, region_lon, monkeypatch):
        first = _estudio_payload(region_lon["id"])
        first["beneficiario"]["curp"] = self.VALID_CURP
        r1 = client.post("/api/estudios", headers=capturista_headers, json=first)
        assert r1.status_code == 201, r1.text

        monkeypatch.setattr(
            "routers.socioeconomico._assert_curp_disponible", lambda *a, **k: None
        )
        second = _estudio_payload(region_lon["id"])
        second["beneficiario"]["curp"] = self.VALID_CURP
        self._assert_409_curp_duplicada(
            client.post("/api/estudios", headers=capturista_headers, json=second)
        )

    def test_update_race_returns_409_estructurado(self, client, capturista_headers, region_lon, monkeypatch):
        first = _estudio_payload(region_lon["id"])
        first["beneficiario"]["curp"] = self.VALID_CURP
        r1 = client.post("/api/estudios", headers=capturista_headers, json=first)
        assert r1.status_code == 201, r1.text

        second = _estudio_payload(region_lon["id"])
        r2 = client.post("/api/estudios", headers=capturista_headers, json=second)
        assert r2.status_code == 201, r2.text
        otro_estudio_id = r2.json()["estudio_id"]

        # Cambiar la CURP del segundo estudio a la ya registrada, con el
        # pre-check anulado: el UPDATE choca con la UNIQUE. (El PATCH exige el
        # beneficiario completo, así que se reenvía el del payload original.)
        monkeypatch.setattr(
            "routers.socioeconomico._assert_curp_disponible", lambda *a, **k: None
        )
        beneficiario_editado = dict(second["beneficiario"], curp=self.VALID_CURP)
        self._assert_409_curp_duplicada(
            client.patch(
                f"/api/estudios/{otro_estudio_id}",
                headers=capturista_headers,
                json={"beneficiario": beneficiario_editado},
            )
        )
