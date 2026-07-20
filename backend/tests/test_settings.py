"""
Unit tests for backend/settings.py (Issue #83 — centralized config module).

settings.py has no external dependencies (stdlib `os` only), so these tests
run even without the DB/Supabase driver stack installed.
"""

import importlib

import pytest

import settings


def test_require_raises_clear_error_when_missing(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    with pytest.raises(settings.MissingSettingError, match="DB_HOST"):
        settings.db_host()


def test_require_returns_value_when_present(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.example.com")
    assert settings.db_host() == "db.example.com"


def test_optional_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("DB_NAME", raising=False)
    assert settings.db_name() == "postgres"


def test_optional_returns_explicit_value(monkeypatch):
    monkeypatch.setenv("DB_NAME", "rotary_prod")
    assert settings.db_name() == "rotary_prod"


def test_db_host_or_none_does_not_raise_when_unset(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    assert settings.db_host_or_none() is None


def test_supabase_settings_require_presence(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    with pytest.raises(settings.MissingSettingError, match="SUPABASE_URL"):
        settings.supabase_url()

    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(settings.MissingSettingError, match="SUPABASE_SERVICE_KEY"):
        settings.supabase_service_key()


def test_resend_api_key_required_only_when_read(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    with pytest.raises(settings.MissingSettingError, match="RESEND_API_KEY"):
        settings.resend_api_key()


def test_app_base_url_falls_back_to_vercel_url(monkeypatch):
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.setenv("VERCEL_URL", "my-preview.vercel.app")
    assert settings.app_base_url() == "https://my-preview.vercel.app"


def test_app_base_url_empty_when_nothing_set(monkeypatch):
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.delenv("VERCEL_URL", raising=False)
    assert settings.app_base_url() == ""


class TestJwtSecretBootValidation:
    """JWT_SECRET is validated once, at settings module import time, so a
    missing/weak secret aborts the app boot with a clear message instead of
    failing deep inside a request handler."""

    def teardown_method(self) -> None:
        # Restore the deterministic test secret conftest.py relies on and
        # reload so later tests see a consistent settings.JWT_SECRET again.
        import os

        os.environ["JWT_SECRET"] = "test-secret-" + ("x" * 32)
        importlib.reload(settings)

    def test_missing_jwt_secret_aborts_import(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            importlib.reload(settings)

    def test_placeholder_jwt_secret_aborts_import(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "dev-secret-change-in-production")
        with pytest.raises(RuntimeError, match="placeholder"):
            importlib.reload(settings)

    def test_short_jwt_secret_aborts_import(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "too-short")
        with pytest.raises(RuntimeError, match="32 bytes"):
            importlib.reload(settings)
