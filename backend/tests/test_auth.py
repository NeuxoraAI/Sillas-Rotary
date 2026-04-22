"""
Integration tests for JWT authentication.

TDD: Tests written BEFORE the implementation of the new auth router.
Spec reference: user-auth specification (fase-1-fundacion).
"""

import pytest


class TestLogin:
    """POST /api/auth/login scenarios."""

    def test_login_valid_credentials_returns_jwt(self, client, admin_user):
        """Valid email+password returns access_token with rol and user info."""
        res = client.post("/api/auth/login", json={
            "email": "admin@test.mx",
            "password": "adminpass123",
        })

        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["rol"] == "admin"
        assert data["nombre"] == "Admin Test"
        assert "usuario_id" in data
        # Token should be a non-empty string
        assert len(data["access_token"]) > 10

    def test_login_wrong_password_returns_401(self, client, capturista_user):
        """Wrong password returns 401 with generic message (no info leakage)."""
        res = client.post("/api/auth/login", json={
            "email": "cap@test.mx",
            "password": "wrongpassword",
        })

        assert res.status_code == 401
        assert "Credenciales inválidas" in res.json()["detail"]

    def test_login_unknown_email_returns_401(self, client):
        """Non-existent email returns 401 — does NOT reveal email doesn't exist."""
        res = client.post("/api/auth/login", json={
            "email": "nobody@nope.mx",
            "password": "whatever",
        })

        assert res.status_code == 401
        assert "Credenciales inválidas" in res.json()["detail"]

    def test_login_inactive_user_returns_401(self, client, _test_db_conn, capturista_user):
        """Deactivated user cannot login."""
        import psycopg2.extras
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "UPDATE usuarios SET activo = FALSE WHERE id = %s",
                (capturista_user["id"],),
            )
        _test_db_conn.commit()

        res = client.post("/api/auth/login", json={
            "email": "cap@test.mx",
            "password": "cappass123",
        })

        assert res.status_code == 401

    def test_login_with_invalid_stored_hash_returns_401_not_500(self, client, _test_db_conn, admin_user):
        """Corrupt password_hash in DB must not crash login with 500."""
        import psycopg2.extras
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "UPDATE usuarios SET password_hash = %s WHERE id = %s",
                ("test123", admin_user["id"]),
            )
        _test_db_conn.commit()

        res = client.post("/api/auth/login", json={
            "email": "admin@test.mx",
            "password": "adminpass123",
        })

        assert res.status_code == 401
        assert "Credenciales inválidas" in res.json()["detail"]

    def test_login_capturista_returns_capturista_rol(self, client, capturista_user):
        """Capturista login returns correct rol."""
        res = client.post("/api/auth/login", json={
            "email": "cap@test.mx",
            "password": "cappass123",
        })

        assert res.status_code == 200
        assert res.json()["rol"] == "capturista"


class TestGetMe:
    """GET /api/auth/me scenarios."""

    def test_me_with_valid_token_returns_user(self, client, admin_headers, admin_user):
        """Valid JWT returns current user data."""
        res = client.get("/api/auth/me", headers=admin_headers)

        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "admin@test.mx"
        assert data["rol"] == "admin"
        assert data["nombre"] == "Admin Test"
        assert "usuario_id" in data

    def test_me_without_token_returns_401(self, client):
        """No Authorization header → 401."""
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        """Garbled token → 401."""
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer notavalidtoken"})
        assert res.status_code == 401


class TestRoleEnforcement:
    """Role-based access control scenarios."""

    def test_admin_can_access_admin_endpoint(self, client, admin_headers):
        """Admin JWT allows accessing admin-only endpoint (POST /api/usuarios)."""
        res = client.post("/api/usuarios", json={
            "nombre": "New User",
            "email": "new@test.mx",
            "password": "password123",
            "rol": "capturista",
        }, headers=admin_headers)

        assert res.status_code == 201

    def test_capturista_blocked_from_admin_endpoint(self, client, capturista_headers):
        """Capturista JWT blocked from admin-only endpoint → 403."""
        res = client.post("/api/usuarios", json={
            "nombre": "Hacker",
            "email": "hacker@test.mx",
            "password": "password123",
            "rol": "admin",
        }, headers=capturista_headers)

        assert res.status_code == 403


class TestRouterRoleGuards:
    def test_tecnico_blocked_from_socioeconomico_create(self, client, tecnico_headers, region_lon):
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "beneficiario": {
                "nombre": "RBAC Auth",
                "fecha_nacimiento": "2001-01-15",
                "diagnostico": "Parálisis cerebral",
                "calle": "Calle Test 123",
                "colonia": "Centro",
                "ciudad": "León",
                "telefonos": "4621234567",
            },
            "tutores": [{"numero_tutor": 1, "nombre": "Tutor", "tiene_imss": True, "tiene_infonavit": False}],
            "estudio": {
                "tuvo_silla_previa": False,
                "elaboro_estudio": "Capturista Test",
                "fecha_estudio": "2026-04-19",
                "status": "borrador",
            },
        }

        res = client.post("/api/estudios", json=payload, headers=tecnico_headers)
        assert res.status_code == 403

    def test_capturista_blocked_from_tecnica_create(self, client, capturista_headers, sample_estudio):
        payload = {
            "beneficiario_id": sample_estudio["beneficiario_id"],
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "status": "borrador",
        }

        res = client.post("/api/solicitudes", json=payload, headers=capturista_headers)
        assert res.status_code == 403
