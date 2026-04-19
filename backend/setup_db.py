"""
Full DB setup for Sillas Rotary v2.

Runs in order:
  1. init_db.py     → creates v1 base tables
  2. migrate_v2.sql → migrates schema to v2 (usuarios, paises, regiones, ...)
  3. seed_v2.py     → inserts admin user + 2 países + 4 regiones

Usage:
    cd backend
    python setup_db.py
"""

import os
import sys


def _load_env_file(path: str) -> None:
    """Minimal .env loader — handles KEY=VALUE lines with quotes, skips comments."""
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes if present
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            os.environ.setdefault(key, value)


# Load .env BEFORE importing modules that read env vars at import time
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
_load_env_file(_ENV_PATH)

import psycopg2

from init_db import init as init_v1
from seed_v2 import seed as seed_v2


def _connect():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )


def apply_migration() -> None:
    sql_path = os.path.join(os.path.dirname(__file__), "migrate_v2.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Sillas Rotary — Full DB Setup")
    print("=" * 60)

    print("\n[1/3] Creating v1 base tables (init_db.py)...")
    init_v1()
    print("  ✅ v1 tables created")

    print("\n[2/3] Applying v2 migration (migrate_v2.sql)...")
    apply_migration()
    print("  ✅ v2 migration applied")

    print("\n[3/3] Seeding admin + países + regiones (seed_v2.py)...")
    seed_v2()

    print("\n" + "=" * 60)
    print("✅ Setup completo. Ya podés hacer login con:")
    print("   Email:    admin@vidaug.mx")
    print("   Password: changeme123")
    print("=" * 60)
