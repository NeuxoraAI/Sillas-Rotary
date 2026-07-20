from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

import settings


def _looks_like_test_value(value: str | None) -> bool:
    if value is None:
        return False
    lowered = value.lower()
    return "test" in lowered


def _is_unsafe_test_schema(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized == "public" or "," in normalized


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

    if _is_unsafe_test_schema(test_schema):
        raise RuntimeError(
            "Unsafe test database target refused: TEST_DB_SCHEMA cannot be public or include multiple schemas."
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
    test_database_url = settings.test_database_url()
    test_schema = settings.test_db_schema()
    db_name = settings.db_name()
    db_host = settings.db_host_or_none()

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

    options = settings.test_db_options()
    if test_schema:
        schema_option = f"-c search_path={test_schema}"
        options = f"{options} {schema_option}".strip() if options else schema_option

    if options:
        conn_kwargs["options"] = options

    return conn_kwargs


def _build_conn_kwargs() -> dict:
    """Build psycopg2 connection kwargs from settings."""
    return dict(
        host=settings.db_host(),
        port=settings.db_port(),
        dbname=settings.db_name(),
        user=settings.db_user(),
        password=settings.db_password(),
        sslmode="require",
    )


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(**_build_conn_kwargs())


class _DBAdapter:
    """Thin adapter so routers can call conn.execute() uniformly."""

    def __init__(self, conn: psycopg2.extensions.connection, cursor: psycopg2.extensions.cursor) -> None:
        self._conn = conn
        self._cur = cursor

    def execute(self, sql: str, params: tuple = ()) -> "_DBAdapter":
        self._cur.execute(sql, params)
        return self

    def fetchone(self) -> dict | None:
        return self._cur.fetchone()  # type: ignore[return-value]

    def fetchall(self) -> list[dict]:
        return self._cur.fetchall()  # type: ignore[return-value]

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()


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
    adapter = _DBAdapter(conn, cur)
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
    adapter = _DBAdapter(conn, cur)
    try:
        yield adapter
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
