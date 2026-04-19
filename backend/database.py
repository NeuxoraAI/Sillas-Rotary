import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras


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
