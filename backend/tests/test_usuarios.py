"""
Integration tests for user management.

TDD: Tests written BEFORE the implementation.
Spec reference: user-management specification (fase-1-fundacion).
"""

import pytest


class TestCreateUser:
    """POST /api/usuarios — admin only."""

    def test_admin_creates_capturista_returns_201(self, client, admin_headers):
        """Admin creates a new capturista user."""
        res = client.post("/api/usuarios", json={
            "nombre": "Nuevo Capturista",
            "email": "nuevo@test.mx",
            "password": "password123",
            "rol": "capturista",
        }, headers=admin_headers)

        assert res.status_code == 201
        data = res.json()
        assert data["nombre"] == "Nuevo Capturista"
        assert data["email"] == "nuevo@test.mx"
        assert data["rol"] == "capturista"
        assert data["activo"] is True
        assert "usuario_id" in data
        # Password must NOT be returned
        assert "password" not in data
        assert "password_hash" not in data

    def test_admin_creates_tecnico(self, client, admin_headers):
        """Admin can create a tecnico user."""
        res = client.post("/api/usuarios", json={
            "nombre": "Técnico Uno",
            "email": "tec1@test.mx",
            "password": "password123",
            "rol": "tecnico",
        }, headers=admin_headers)

        assert res.status_code == 201
        assert res.json()["rol"] == "tecnico"

    def test_duplicate_email_returns_409(self, client, admin_headers, capturista_user):
        """Creating a user with an existing email returns 409."""
        res = client.post("/api/usuarios", json={
            "nombre": "Duplicado",
            "email": "cap@test.mx",  # already exists from capturista_user fixture
            "password": "password123",
            "rol": "capturista",
        }, headers=admin_headers)

        assert res.status_code == 409
        assert "email" in res.json()["detail"].lower()

    def test_capturista_cannot_create_user(self, client, capturista_headers):
        """Non-admin users get 403 when trying to create users."""
        res = client.post("/api/usuarios", json={
            "nombre": "Intruso",
            "email": "intruso@test.mx",
            "password": "password123",
            "rol": "capturista",
        }, headers=capturista_headers)

        assert res.status_code == 403

    def test_invalid_rol_returns_422(self, client, admin_headers):
        """Creating user with invalid rol returns 422 validation error."""
        res = client.post("/api/usuarios", json={
            "nombre": "Bad Rol",
            "email": "badrol@test.mx",
            "password": "password123",
            "rol": "superadmin",  # invalid
        }, headers=admin_headers)

        assert res.status_code == 422


class TestListUsers:
    """GET /api/usuarios — admin only."""

    def test_list_returns_all_users(self, client, admin_headers, admin_user, capturista_user):
        """Returns all users including inactive ones."""
        res = client.get("/api/usuarios", headers=admin_headers)

        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2  # admin_user + capturista_user from fixtures

    def test_list_includes_activo_field(self, client, admin_headers, admin_user):
        """Each user in the list has activo field."""
        res = client.get("/api/usuarios", headers=admin_headers)
        users = res.json()
        assert all("activo" in u for u in users)

    def test_capturista_cannot_list_users(self, client, capturista_headers):
        """Non-admin cannot list users → 403."""
        res = client.get("/api/usuarios", headers=capturista_headers)
        assert res.status_code == 403


class TestDeactivateUser:
    """DELETE /api/usuarios/{id} — admin only (soft delete)."""

    def test_admin_deactivates_user(self, client, admin_headers, capturista_user):
        """Admin can deactivate a user (soft delete)."""
        user_id = capturista_user["id"]
        res = client.delete(f"/api/usuarios/{user_id}", headers=admin_headers)

        assert res.status_code == 200
        data = res.json()
        assert data["activo"] is False

    def test_deactivated_user_cannot_login(self, client, admin_headers, capturista_user):
        """Once deactivated, user cannot login."""
        user_id = capturista_user["id"]
        client.delete(f"/api/usuarios/{user_id}", headers=admin_headers)

        res = client.post("/api/auth/login", json={
            "email": "cap@test.mx",
            "password": "cappass123",
        })
        assert res.status_code == 401

    def test_deactivate_nonexistent_user_returns_404(self, client, admin_headers):
        """Trying to deactivate a non-existent user returns 404."""
        res = client.delete("/api/usuarios/99999", headers=admin_headers)
        assert res.status_code == 404

    def test_capturista_cannot_deactivate_user(self, client, capturista_headers, admin_user):
        """Capturista cannot deactivate users → 403."""
        res = client.delete(f"/api/usuarios/{admin_user['id']}", headers=capturista_headers)
        assert res.status_code == 403
