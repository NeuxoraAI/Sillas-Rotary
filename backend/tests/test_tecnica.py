def _solicitud_payload(beneficiario_id: int) -> dict:
    return {
        "beneficiario_id": beneficiario_id,
        "entorno": "Urbano / Interiores",
        "control_tronco": "Completo",
        "control_cabeza": "Independiente",
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
