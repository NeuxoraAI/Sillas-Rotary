"""
Integration tests for the email-onboarding / password self-service flows.

TDD: tests written alongside routers/password.py. Email delivery is always
mocked (no Resend calls). Expiry/used-token scenarios use direct DB inserts of
tokens with a controlled raw value (we store only its sha256 hash) rather than
sleeping or patching the clock.

Covers:
- Resend invitation (admin-only, Pendiente-only, 409 on active)
- Set-password activation (tipo-lock, expiry, single-use, deactivated guard)
- Forgot/reset (enumeration-safe, tipo-lock, expiry, invalidation on reissue)
- Change password (all 4 roles, wrong-current, too-short, unauthenticated)
- _verify_password NULL/empty-hash hardening
"""

from unittest.mock import patch

import psycopg2.extras
import pytest

from routers.auth import _verify_password
from utils.tokens import hash_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_pending_user(client, admin_headers, email, rol="capturista"):
    """Create a passwordless (Pendiente) user; return (usuario_id, raw_token)."""
    with patch("routers.usuarios.send_invite") as mock_invite:
        res = client.post("/api/usuarios", json={
            "nombre": "Pendiente Test",
            "email": email,
            "rol": rol,
        }, headers=admin_headers)
    assert res.status_code == 201, res.text
    raw_token = mock_invite.call_args.args[1]
    return res.json()["usuario_id"], raw_token


def _insert_token(conn, usuario_id, raw, tipo, interval, used=False):
    """Insert a token directly with a controlled raw value and relative expiry.

    `interval` is a Postgres interval string, e.g. '72 hours' or '-1 hour'
    (negative → already expired). `used=True` stamps used_at=NOW().
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO password_tokens (usuario_id, token_hash, tipo, expires_at, used_at)
            VALUES (%s, %s, %s, NOW() + %s::interval,
                    CASE WHEN %s THEN NOW() ELSE NULL END)
            """,
            (usuario_id, hash_token(raw), tipo, interval, used),
        )
    conn.commit()


def _token_used_at(conn, raw):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT used_at FROM password_tokens WHERE token_hash = %s", (hash_token(raw),))
        row = cur.fetchone()
    conn.commit()
    return row["used_at"] if row else "MISSING"


# ---------------------------------------------------------------------------
# Resend invitation
# ---------------------------------------------------------------------------

class TestResendInvitation:
    def test_reenviar_invite_non_admin_403(self, client, capturista_headers, admin_headers):
        uid, _ = _create_pending_user(client, admin_headers, "resend403@test.mx")
        res = client.post(f"/api/usuarios/{uid}/reenviar-invitacion", headers=capturista_headers)
        assert res.status_code == 403

    def test_reenviar_invite_admin_204_invalidates_prior(self, client, admin_headers, _test_db_conn):
        uid, first_raw = _create_pending_user(client, admin_headers, "resend204@test.mx")
        with patch("routers.password.send_invite") as mock_invite:
            res = client.post(f"/api/usuarios/{uid}/reenviar-invitacion", headers=admin_headers)
        assert res.status_code == 204
        mock_invite.assert_called_once()
        # Prior invite token invalidated (used_at stamped).
        assert _token_used_at(_test_db_conn, first_raw) is not None
        # New token issued and still unused.
        new_raw = mock_invite.call_args.args[1]
        assert _token_used_at(_test_db_conn, new_raw) is None

    def test_reenviar_invite_active_user_409(self, client, admin_headers, capturista_user):
        # capturista_user is created active (with password) by the fixture.
        res = client.post(f"/api/usuarios/{capturista_user['id']}/reenviar-invitacion", headers=admin_headers)
        assert res.status_code == 409
        assert "activo" in res.json()["detail"].lower()

    def test_reenviar_invite_404_missing_user(self, client, admin_headers):
        res = client.post("/api/usuarios/99999/reenviar-invitacion", headers=admin_headers)
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Set-password activation
# ---------------------------------------------------------------------------

class TestSetPassword:
    def test_valid_token_activates_account(self, client, admin_headers, _test_db_conn):
        uid, raw = _create_pending_user(client, admin_headers, "setpw@test.mx")
        res = client.post("/api/auth/set-password", json={"token": raw, "password": "brandnew123"})
        assert res.status_code == 200
        # Account is now active and token consumed.
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT activo, password_hash FROM usuarios WHERE id = %s", (uid,))
            user = cur.fetchone()
        _test_db_conn.commit()
        assert user["activo"] is True
        assert user["password_hash"] is not None
        assert _token_used_at(_test_db_conn, raw) is not None

    def test_valid_token_then_login(self, client, admin_headers):
        _create_pending_user(client, admin_headers, "setpwlogin@test.mx")
        # Re-fetch the raw token from the create mock is not available here; issue
        # a fresh invite via resend to capture the raw token cleanly.
        # (create above already consumed the mock context.)
        uid, raw = _create_pending_user(client, admin_headers, "setpwlogin2@test.mx")
        client.post("/api/auth/set-password", json={"token": raw, "password": "loginpass123"})
        login = client.post("/api/auth/login", json={"email": "setpwlogin2@test.mx", "password": "loginpass123"})
        assert login.status_code == 200
        assert "access_token" in login.json()

    def test_expired_token_400_not_consumed(self, client, admin_headers, _test_db_conn):
        uid, _ = _create_pending_user(client, admin_headers, "setpwexp@test.mx")
        raw = "expired-invite-token"
        _insert_token(_test_db_conn, uid, raw, "invite", "-1 hour")
        res = client.post("/api/auth/set-password", json={"token": raw, "password": "whatever123"})
        assert res.status_code == 400
        assert _token_used_at(_test_db_conn, raw) is None  # not consumed

    def test_already_used_token_400(self, client, admin_headers, _test_db_conn):
        uid, _ = _create_pending_user(client, admin_headers, "setpwused@test.mx")
        raw = "used-invite-token"
        _insert_token(_test_db_conn, uid, raw, "invite", "72 hours", used=True)
        res = client.post("/api/auth/set-password", json={"token": raw, "password": "whatever123"})
        assert res.status_code == 400

    def test_wrong_tipo_400(self, client, admin_headers, _test_db_conn):
        """A reset token must not redeem on the set-password (invite) path."""
        uid, _ = _create_pending_user(client, admin_headers, "setpwtipo@test.mx")
        raw = "reset-token-on-invite-path"
        _insert_token(_test_db_conn, uid, raw, "reset", "72 hours")
        res = client.post("/api/auth/set-password", json={"token": raw, "password": "whatever123"})
        assert res.status_code == 400

    def test_deactivated_user_400(self, client, admin_headers, capturista_user, _test_db_conn):
        """An invite token pointing at a user who already has a password (active
        or later deactivated) must not re-activate the account."""
        raw = "invite-for-active-user"
        _insert_token(_test_db_conn, capturista_user["id"], raw, "invite", "72 hours")
        res = client.post("/api/auth/set-password", json={"token": raw, "password": "whatever123"})
        assert res.status_code == 400

    def test_password_too_short_422(self, client, admin_headers):
        uid, raw = _create_pending_user(client, admin_headers, "setpwshort@test.mx")
        res = client.post("/api/auth/set-password", json={"token": raw, "password": "short"})
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# Forgot / reset
# ---------------------------------------------------------------------------

class TestForgotReset:
    def test_forgot_known_active_email_200_sends(self, client, capturista_user, _test_db_conn):
        with patch("routers.password.send_reset") as mock_reset:
            res = client.post("/api/auth/forgot-password", json={"email": "cap@test.mx"})
        assert res.status_code == 200
        mock_reset.assert_called_once()
        raw = mock_reset.call_args.args[1]
        assert _token_used_at(_test_db_conn, raw) is None

    def test_forgot_unknown_email_200_identical_no_token(self, client):
        with patch("routers.password.send_reset") as mock_reset:
            res = client.post("/api/auth/forgot-password", json={"email": "ghost@test.mx"})
        assert res.status_code == 200
        assert res.json()["message"] == "Si el email existe, recibirás instrucciones en breve."
        mock_reset.assert_not_called()

    def test_forgot_pending_user_200_no_token(self, client, admin_headers):
        _create_pending_user(client, admin_headers, "forgotpending@test.mx")
        with patch("routers.password.send_reset") as mock_reset:
            res = client.post("/api/auth/forgot-password", json={"email": "forgotpending@test.mx"})
        assert res.status_code == 200
        mock_reset.assert_not_called()

    def test_reset_valid_token_200_activo_unchanged(self, client, capturista_user, _test_db_conn):
        with patch("routers.password.send_reset") as mock_reset:
            client.post("/api/auth/forgot-password", json={"email": "cap@test.mx"})
        raw = mock_reset.call_args.args[1]
        res = client.post("/api/auth/reset-password", json={"token": raw, "password": "resetpass123"})
        assert res.status_code == 200
        # New password works; activo unchanged (still active).
        login = client.post("/api/auth/login", json={"email": "cap@test.mx", "password": "resetpass123"})
        assert login.status_code == 200
        assert _token_used_at(_test_db_conn, raw) is not None

    def test_reset_expired_token_400(self, client, capturista_user, _test_db_conn):
        raw = "expired-reset-token"
        _insert_token(_test_db_conn, capturista_user["id"], raw, "reset", "-1 hour")
        res = client.post("/api/auth/reset-password", json={"token": raw, "password": "whatever123"})
        assert res.status_code == 400

    def test_reset_wrong_tipo_400(self, client, capturista_user, _test_db_conn):
        """An invite token must not redeem on the reset path."""
        raw = "invite-token-on-reset-path"
        _insert_token(_test_db_conn, capturista_user["id"], raw, "invite", "72 hours")
        res = client.post("/api/auth/reset-password", json={"token": raw, "password": "whatever123"})
        assert res.status_code == 400

    def test_reset_already_used_400(self, client, capturista_user, _test_db_conn):
        raw = "used-reset-token"
        _insert_token(_test_db_conn, capturista_user["id"], raw, "reset", "1 hour", used=True)
        res = client.post("/api/auth/reset-password", json={"token": raw, "password": "whatever123"})
        assert res.status_code == 400

    def test_reset_token_invalidated_on_reissue(self, client, capturista_user, _test_db_conn):
        """Requesting a second reset invalidates the first token."""
        with patch("routers.password.send_reset") as m1:
            client.post("/api/auth/forgot-password", json={"email": "cap@test.mx"})
        first_raw = m1.call_args.args[1]
        with patch("routers.password.send_reset") as m2:
            client.post("/api/auth/forgot-password", json={"email": "cap@test.mx"})
        second_raw = m2.call_args.args[1]

        # First token now rejected.
        res_first = client.post("/api/auth/reset-password", json={"token": first_raw, "password": "firstpass123"})
        assert res_first.status_code == 400
        # Second token works.
        res_second = client.post("/api/auth/reset-password", json={"token": second_raw, "password": "secondpass123"})
        assert res_second.status_code == 200

    def test_reset_password_too_short_422(self, client, capturista_user, _test_db_conn):
        raw = "reset-short-token"
        _insert_token(_test_db_conn, capturista_user["id"], raw, "reset", "1 hour")
        res = client.post("/api/auth/reset-password", json={"token": raw, "password": "short"})
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# Change password (authenticated)
# ---------------------------------------------------------------------------

class TestChangePassword:
    def test_correct_current_204(self, client, capturista_headers):
        res = client.post("/api/me/password", json={
            "current_password": "cappass123",
            "new_password": "changedpass123",
        }, headers=capturista_headers)
        assert res.status_code == 204
        # New password works for login.
        login = client.post("/api/auth/login", json={"email": "cap@test.mx", "password": "changedpass123"})
        assert login.status_code == 200

    def test_wrong_current_400(self, client, capturista_headers):
        res = client.post("/api/me/password", json={
            "current_password": "wrongpassword",
            "new_password": "changedpass123",
        }, headers=capturista_headers)
        assert res.status_code == 400

    def test_new_too_short_422(self, client, capturista_headers):
        res = client.post("/api/me/password", json={
            "current_password": "cappass123",
            "new_password": "short",
        }, headers=capturista_headers)
        assert res.status_code == 422

    def test_unauthenticated_401(self, client):
        res = client.post("/api/me/password", json={
            "current_password": "x", "new_password": "changedpass123",
        })
        assert res.status_code == 401

    @pytest.mark.parametrize("hdr_fixture,email,current_pw", [
        ("admin_headers", "admin@test.mx", "adminpass123"),
        ("capturista_headers", "cap@test.mx", "cappass123"),
        ("tecnico_headers", "tec@test.mx", "tecpass123"),
        ("organizacion_headers", "org@test.mx", "orgpass123"),
    ])
    def test_all_four_roles(self, client, request, hdr_fixture, email, current_pw):
        headers = request.getfixturevalue(hdr_fixture)
        res = client.post("/api/me/password", json={
            "current_password": current_pw,
            "new_password": "newrolepass123",
        }, headers=headers)
        assert res.status_code == 204


# ---------------------------------------------------------------------------
# _verify_password hardening
# ---------------------------------------------------------------------------

class TestVerifyPasswordHardening:
    def test_none_hash_returns_false(self):
        assert _verify_password("anything", None) is False

    def test_empty_string_hash_returns_false(self):
        assert _verify_password("anything", "") is False
