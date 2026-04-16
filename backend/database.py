import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )


class _DBAdapter:
    """Thin adapter so routers can call conn.execute() just like sqlite3."""

    def __init__(self, cursor: psycopg2.extensions.cursor) -> None:
        self._cur = cursor

    def execute(self, sql: str, params: tuple = ()) -> "_DBAdapter":
        self._cur.execute(sql, params)
        return self

    def fetchone(self) -> dict | None:
        return self._cur.fetchone()  # type: ignore[return-value]

    def fetchall(self) -> list[dict]:
        return self._cur.fetchall()  # type: ignore[return-value]


@contextmanager
def get_db() -> Generator[_DBAdapter, None, None]:
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
