"""
Centralized configuration/secrets module (Issue #83).

Before this module existed, `DB_*`, `SUPABASE_*`, `JWT_SECRET` and friends
were read via scattered `os.environ[...]` / `os.environ.get(...)` calls across
routers and scripts. That made it impossible to swap the config source (env
vars today, AWS Secrets Manager / GCP Secret Manager tomorrow) without
touching every call site.

The rest of the codebase must import values from here instead of calling
`os.environ` directly. To change the source later, only this file changes.

Required settings are read lazily (on each call, not at import) so that
`monkeypatch.setenv(...)` in tests keeps working and importing this module
never has side effects beyond the JWT_SECRET boot check below, which mirrors
the fail-fast validation `routers/auth.py` already performed before this
module existed.
"""

import os


class MissingSettingError(RuntimeError):
    """Raised when a required environment variable is not set."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"Falta la variable de entorno requerida '{name}'. "
            "La aplicación no puede continuar sin ella."
        )


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise MissingSettingError(name)
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# ---------------------------------------------------------------------------
# App / runtime
# ---------------------------------------------------------------------------

def env() -> str:
    return _optional("ENV", "development").lower()


# ---------------------------------------------------------------------------
# Database — direct psycopg2 connection (backend/database.py + bootstrap
# scripts: init_db.py, setup_db.py, seed_v2.py)
# ---------------------------------------------------------------------------

def db_host() -> str:
    return _require("DB_HOST")


def db_host_or_none() -> str | None:
    """Non-raising read of DB_HOST for heuristics (e.g. 'does this look like
    a test target') where an unset value is a valid state, not an error."""
    return os.environ.get("DB_HOST")


def db_port() -> int:
    return int(_optional("DB_PORT", "5432"))


def db_name() -> str:
    return _optional("DB_NAME", "postgres")


def db_user() -> str:
    return _optional("DB_USER", "postgres")


def db_password() -> str:
    return _require("DB_PASSWORD")


# ---------------------------------------------------------------------------
# Test database overrides (backend/tests) — not production secrets, but
# centralized here too so database.py has a single settings import.
# ---------------------------------------------------------------------------

def test_database_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL")


def test_db_schema() -> str | None:
    return os.environ.get("TEST_DB_SCHEMA")


def test_db_options() -> str | None:
    return os.environ.get("TEST_DB_OPTIONS")


# ---------------------------------------------------------------------------
# Supabase Storage — blobs only (fotos-tecnica, documentos-estudio buckets)
# ---------------------------------------------------------------------------

def supabase_url() -> str:
    return _require("SUPABASE_URL")


def supabase_service_key() -> str:
    return _require("SUPABASE_SERVICE_KEY")


# ---------------------------------------------------------------------------
# JWT auth — validated eagerly at import time so the process fails fast on
# boot with a clear message instead of failing deep inside a request handler.
# ---------------------------------------------------------------------------

JWT_ALGORITHM = "HS256"

_jwt_secret = os.environ.get("JWT_SECRET")
if not _jwt_secret or _jwt_secret == "dev-secret-change-in-production":
    raise RuntimeError(
        "JWT_SECRET environment variable must be set to a strong secret "
        "(>=32 bytes). The placeholder 'dev-secret-change-in-production' is "
        "not accepted."
    )
if len(_jwt_secret) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 bytes long.")

JWT_SECRET = _jwt_secret
JWT_EXPIRE_HOURS = int(_optional("JWT_EXPIRE_HOURS", "8"))


# ---------------------------------------------------------------------------
# Email delivery (Resend) — backend/utils/email.py
# ---------------------------------------------------------------------------

def resend_api_key() -> str:
    """Required only when an email is actually sent (fail-open callers)."""
    return _require("RESEND_API_KEY")


def email_from() -> str:
    return _optional("EMAIL_FROM", "onboarding@resend.dev")


def app_base_url() -> str:
    """APP_BASE_URL without a trailing slash. Falls back to the
    Vercel-injected deployment URL so preview deployments build working
    email links without per-branch configuration."""
    explicit = _optional("APP_BASE_URL").rstrip("/")
    if explicit:
        return explicit
    vercel = _optional("VERCEL_URL")
    return f"https://{vercel}" if vercel else ""
