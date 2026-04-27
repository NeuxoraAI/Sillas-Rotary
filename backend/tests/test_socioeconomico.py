def _estudio_payload(region_id: int) -> dict:
    return {
        "region_id": region_id,
        "sede": "León sede Forum",
        "beneficiario": {
            "nombre": "Beneficiario RBAC",
            "fecha_nacimiento": "2001-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "telefonos": "4621234567",
        },
        "tutores": [
            {
                "numero_tutor": 1,
                "nombre": "Tutor RBAC",
                "tiene_imss": True,
                "tiene_infonavit": False,
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
        payload["tutores"][0]["ingreso_mensual"] = 12500.0
        payload["tutores"].append(
            {
                "numero_tutor": 2,
                "nombre": "Tutor Secundario",
                "ingreso_mensual": 8400.5,
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
        assert tutor_by_num[1]["ingreso_mensual"] == 12500.0
        assert tutor_by_num[2]["ingreso_mensual"] == 8400.5
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
