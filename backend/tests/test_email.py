"""
Unit tests for backend/utils/email.py.

TDD: tests written BEFORE wiring the email module into the routers.
These never hit the network — httpx.post is mocked. They assert the request
shape (endpoint, auth header, from/to/subject/html) and that EmailDeliveryError
is raised on timeout and HTTP errors so call sites can fail-open.
"""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from utils import email as email_mod
from utils.email import EmailDeliveryError, send_invite, send_reset


@pytest.fixture(autouse=True)
def _email_env(monkeypatch):
    """Deterministic email env for every test in this module."""
    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")
    monkeypatch.setenv("EMAIL_FROM", "onboarding@resend.dev")
    monkeypatch.setenv("APP_BASE_URL", "https://app.example.com")


def _ok_response() -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    return resp


class TestSendInvite:
    def test_posts_to_resend_with_auth_and_body(self):
        with patch.object(email_mod.httpx, "post", return_value=_ok_response()) as mock_post:
            send_invite("user@example.com", "raw-token-abc", "Ana Pérez")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.resend.com/emails"
        assert kwargs["headers"]["Authorization"] == "Bearer test-resend-key"
        assert kwargs["timeout"] == 10.0
        body = kwargs["json"]
        assert body["from"] == "onboarding@resend.dev"
        assert body["to"] == ["user@example.com"]
        assert body["subject"] == "Bienvenido/a — Activá tu cuenta"
        # Activation link points at set-password.html with the raw token.
        assert "https://app.example.com/set-password.html?token=raw-token-abc" in body["html"]
        assert "72 horas" in body["html"]
        # Personalized greeting with the user's name (spec requirement).
        assert "Ana Pérez" in body["html"]

    def test_relative_link_when_base_url_unset(self, monkeypatch):
        monkeypatch.delenv("APP_BASE_URL", raising=False)
        with patch.object(email_mod.httpx, "post", return_value=_ok_response()) as mock_post:
            send_invite("user@example.com", "tok", "Ana")
        body = mock_post.call_args.kwargs["json"]
        assert body["html"].count("/set-password.html?token=tok") == 1


class TestSendReset:
    def test_posts_reset_body(self):
        with patch.object(email_mod.httpx, "post", return_value=_ok_response()) as mock_post:
            send_reset("user@example.com", "reset-token-xyz")

        body = mock_post.call_args.kwargs["json"]
        assert body["subject"] == "Recuperación de contraseña"
        assert "https://app.example.com/reset-password.html?token=reset-token-xyz" in body["html"]
        assert "1 hora" in body["html"]


class TestFailureModes:
    def test_timeout_raises_email_delivery_error(self):
        with patch.object(email_mod.httpx, "post", side_effect=httpx.TimeoutException("boom")):
            with pytest.raises(EmailDeliveryError):
                send_invite("user@example.com", "tok", "Ana")

    def test_http_error_raises_email_delivery_error(self):
        resp = MagicMock()
        err = httpx.HTTPStatusError("bad", request=MagicMock(), response=MagicMock(status_code=500))
        resp.raise_for_status.side_effect = err
        with patch.object(email_mod.httpx, "post", return_value=resp):
            with pytest.raises(EmailDeliveryError):
                send_reset("user@example.com", "tok")

    def test_transport_error_raises_email_delivery_error(self):
        with patch.object(email_mod.httpx, "post", side_effect=httpx.ConnectError("no route")):
            with pytest.raises(EmailDeliveryError):
                send_invite("user@example.com", "tok", "Ana")
