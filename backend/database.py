import os
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras


def _looks_like_test_value(value: str | None) -> bool:
    if value is None:
        return False
    lowered = value.lower()
    return "test" in lowered


def assert_test_database_target(
    *,
    db_name: str | None,
    db_host: str | None,
    test_database_url: str | None,
    test_schema: str | None,
) -> None:
    """
    Fail fast when tests are not explicitly scoped to test resources.

    Allowed test scopes:
    - TEST_DATABASE_URL set to a URL whose db name contains "test"
    - TEST_DB_SCHEMA set to a schema name containing "test"
    - Fallback DB_NAME/DB_HOST already contain "test"
    """
    if test_database_url:
        parsed = urlparse(test_database_url)
        candidate_db = parsed.path.lstrip("/")
        if _looks_like_test_value(candidate_db) or _looks_like_test_value(parsed.hostname):
            return
        raise RuntimeError(
            "Unsafe test database target refused: TEST_DATABASE_URL does not look test-scoped."
        )

    if _looks_like_test_value(test_schema):
        return

    if _looks_like_test_value(db_name) or _looks_like_test_value(db_host):
        return

    raise RuntimeError(
        "Unsafe test database target refused: configure TEST_DATABASE_URL or TEST_DB_SCHEMA."
    )


def build_test_conn_kwargs() -> dict:
    """Build connection kwargs for tests honoring TEST_DATABASE_URL and schema guardrails."""
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    test_schema = os.environ.get("TEST_DB_SCHEMA")
    db_name = os.environ.get("DB_NAME", "postgres")
    db_host = os.environ.get("DB_HOST")

    assert_test_database_target(
        db_name=db_name,
        db_host=db_host,
        test_database_url=test_database_url,
        test_schema=test_schema,
    )

    if test_database_url:
        conn_kwargs = {"dsn": test_database_url}
    else:
        conn_kwargs = _build_conn_kwargs()

    options = os.environ.get("TEST_DB_OPTIONS")
    if test_schema:
        schema_option = f"-c search_path={test_schema},public"
        options = f"{options} {schema_option}".strip() if options else schema_option

    if options:
        conn_kwargs["options"] = options

    return conn_kwargs


def _build_conn_kwargs() -> dict:
    """Build psycopg2 connection kwargs from environment variables."""
    return dict(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(**_build_conn_kwargs())


class _DBAdapter:
    """Thin adapter so routers can call conn.execute() uniformly."""

    def __init__(self, cursor: psycopg2.extensions.cursor) -> None:
        self._cur = cursor

    def execute(self, sql: str, params: tuple = ()) -> "_DBAdapter":
        self._cur.execute(sql, params)
        return self

    def fetchone(self) -> dict | None:
        return self._cur.fetchone()  # type: ignore[return-value]

    def fetchall(self) -> list[dict]:
        return self._cur.fetchall()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# FastAPI Depends()-compatible generator
# Usage in routers: db: Annotated[_DBAdapter, Depends(get_db)]
# Override in tests: app.dependency_overrides[get_db] = lambda: test_adapter
# ---------------------------------------------------------------------------

def get_db() -> Generator["_DBAdapter", None, None]:
    """
    FastAPI dependency that provides a database adapter.

    Yields a _DBAdapter wrapping a psycopg2 cursor. Commits on success,
    rolls back on exception, always closes the connection.
    """
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    adapter = _DBAdapter(cur)
    try:
        yield adapter
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Legacy context manager — kept for migration compatibility
# Prefer Depends(get_db) in all new code.
# ---------------------------------------------------------------------------

@contextmanager
def get_db_ctx() -> Generator["_DBAdapter", None, None]:
    """Context manager version of get_db. Use Depends(get_db) for new code."""
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    adapter = _DBAdapter(cur)
    try:
        yield adapter
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
