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

    def test_admin_creates_organizacion_user(self, client, admin_headers):
        """Admin can create a user with rol=organizacion."""
        res = client.post("/api/usuarios", json={
            "nombre": "ONG Rotary",
            "email": "ong@test.mx",
            "password": "password123",
            "rol": "organizacion",
        }, headers=admin_headers)

        assert res.status_code == 201
        data = res.json()
        assert data["rol"] == "organizacion"
        assert data["nombre"] == "ONG Rotary"
        assert data["activo"] is True

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


class TestUpdateUser:
    """PATCH /api/usuarios/{id} — admin only."""

    def test_admin_edits_nombre(self, client, admin_headers, capturista_user):
        """Admin can rename a user."""
        uid = capturista_user["id"]
        res = client.patch(f"/api/usuarios/{uid}", json={"nombre": "Capturista Renombrado"}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["nombre"] == "Capturista Renombrado"

    def test_admin_edits_email(self, client, admin_headers, capturista_user):
        """Admin can change a user's email."""
        uid = capturista_user["id"]
        res = client.patch(f"/api/usuarios/{uid}", json={"email": "nuevo@cap.mx"}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["email"] == "nuevo@cap.mx"

    def test_admin_edits_rol(self, client, admin_headers, capturista_user):
        """Admin can change a user's rol."""
        uid = capturista_user["id"]
        res = client.patch(f"/api/usuarios/{uid}", json={"rol": "tecnico"}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["rol"] == "tecnico"

    def test_admin_reactivates_user(self, client, admin_headers, capturista_user):
        """Admin can reactivate a previously deactivated user."""
        uid = capturista_user["id"]
        # Deactivate first
        client.delete(f"/api/usuarios/{uid}", headers=admin_headers)
        # Now reactivate via PATCH
        res = client.patch(f"/api/usuarios/{uid}", json={"activo": True}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["activo"] is True

    def test_admin_resets_password(self, client, admin_headers):
        """Admin can reset a user's password; new password works for login."""
        # Use a dedicated fresh user to avoid shared-state password pollution
        create = client.post("/api/usuarios", json={
            "nombre": "Reset Test",
            "email": "reset@test.mx",
            "password": "original123",
            "rol": "capturista",
        }, headers=admin_headers)
        assert create.status_code == 201
        uid = create.json()["usuario_id"]

        res = client.patch(f"/api/usuarios/{uid}", json={"password": "nuevapass123"}, headers=admin_headers)
        assert res.status_code == 200
        login = client.post("/api/auth/login", json={"email": "reset@test.mx", "password": "nuevapass123"})
        assert login.status_code == 200

    def test_duplicate_email_on_edit_returns_409(self, client, admin_headers, capturista_user, tecnico_user):
        """Editing a user's email to an already-taken email returns 409."""
        uid = capturista_user["id"]
        res = client.patch(f"/api/usuarios/{uid}", json={"email": "tec@test.mx"}, headers=admin_headers)
        assert res.status_code == 409

    def test_admin_cannot_deactivate_self(self, client, admin_headers, admin_user):
        """Admin cannot deactivate their own account via PATCH."""
        uid = admin_user["id"]
        res = client.patch(f"/api/usuarios/{uid}", json={"activo": False}, headers=admin_headers)
        assert res.status_code == 403

    def test_admin_cannot_demote_own_rol(self, client, admin_headers, admin_user):
        """Admin cannot change their own rol away from admin."""
        uid = admin_user["id"]
        res = client.patch(f"/api/usuarios/{uid}", json={"rol": "capturista"}, headers=admin_headers)
        assert res.status_code == 403

    def test_nonexistent_user_returns_404(self, client, admin_headers):
        """PATCH on non-existent user returns 404."""
        res = client.patch("/api/usuarios/99999", json={"nombre": "No existe"}, headers=admin_headers)
        assert res.status_code == 404

    def test_capturista_cannot_edit_users(self, client, capturista_headers, admin_user):
        """Non-admin cannot edit users → 403."""
        res = client.patch(f"/api/usuarios/{admin_user['id']}", json={"nombre": "Nombre Hackeado"}, headers=capturista_headers)
        assert res.status_code == 403


class TestHardDeleteUser:
    """DELETE /api/usuarios/{id}?permanent=true — admin only."""

    def test_admin_hard_deletes_unreferenced_user(self, client, admin_headers, capturista_user):
        """Admin can permanently delete a user that has no associated records."""
        uid = capturista_user["id"]
        res = client.delete(f"/api/usuarios/{uid}?permanent=true", headers=admin_headers)
        assert res.status_code == 200
        # Confirm gone from list
        lst = client.get("/api/usuarios", headers=admin_headers).json()
        assert not any(u["usuario_id"] == uid for u in lst)

    def test_hard_delete_referenced_user_returns_409(self, client, admin_headers, capturista_user,
                                                      region_lon, pais_mx, capturista_headers):
        """Permanently deleting a user with associated estudios returns 409."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "ciudad_registro": "LEON, GTO",
            "beneficiario": {
                "nombres": "Bene Hard",
                "apellido_paterno": "TEST",
                "apellido_materno": "MUESTRA",
                "fecha_nacimiento": "2000-01-15",
                "diagnostico": "PARALISIS CEREBRAL",
                "calle": "CALLE TEST 123",
                "num_ext": "12A",
                "colonia": "CENTRO",
                "ciudad": "LEON",
                "estado_codigo": "11",
                "sexo": "M",
                "telefonos": "4621234567",
            },
            "tutores": [
                {
                    "numero_tutor": 1,
                    "nombres": "TUTOR",
                    "apellido_paterno": "TEST",
                    "apellido_materno": "MUESTRA",
                    "edad": 45,
                    "nivel_estudios": "LICENCIATURA",
                    "estado_civil": "CASADO",
                    "num_hijos": 2,
                    "vivienda": "PROPIA",
                    "fuente_empleo": "EMPLEADO",
                    "ingreso_mensual": 12000,
                    "tiene_imss": True,
                    "tiene_infonavit": False,
                }
            ],
            "estudio": {
                "otras_fuentes_ingreso": "NINGUNA",
                "monto_otras_fuentes": None,
                "tuvo_silla_previa": False,
                "como_obtuvo_silla": None,
                "elaboro_estudio": "CAPTURISTA TEST",
                "fecha_estudio": "2026-04-18",
                "status": "completo",
            },
        }
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201

        uid = capturista_user["id"]
        res = client.delete(f"/api/usuarios/{uid}?permanent=true", headers=admin_headers)
        assert res.status_code == 409
        assert "desact" in res.json()["detail"].lower()

    def test_admin_cannot_hard_delete_self(self, client, admin_headers, admin_user):
        """Admin cannot hard-delete their own account."""
        uid = admin_user["id"]
        res = client.delete(f"/api/usuarios/{uid}?permanent=true", headers=admin_headers)
        assert res.status_code == 403

    def test_nonexistent_user_hard_delete_returns_404(self, client, admin_headers):
        """Permanent delete on non-existent user returns 404."""
        res = client.delete("/api/usuarios/99999?permanent=true", headers=admin_headers)
        assert res.status_code == 404
