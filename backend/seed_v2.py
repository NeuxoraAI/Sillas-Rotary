"""
Seed script for Sillas Rotary v2.

Inserts:
- 2 países (México, USA)
- 4 regiones (LON/León, IRA/Irapuato, PRL/Pearland, HOU/Houston)
- 1 admin user (admin@vidaug.mx / changeme123)

Run AFTER migrate_v2.sql:
    cd backend
    python seed_v2.py

Requires DB_HOST, DB_PASSWORD env vars (same as production).
"""

import os
import sys

import psycopg2
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _connect():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )


def seed():
    conn = _connect()
    cur = conn.cursor()

    print("🌱 Seeding Sillas Rotary v2...")

    # 1. Países
    cur.execute(
        "INSERT INTO paises (nombre, codigo) VALUES (%s, %s) ON CONFLICT (codigo) DO NOTHING RETURNING id",
        ("México", "MX"),
    )
    row = cur.fetchone()
    if row:
        mx_id = row[0]
        print(f"  ✅ País: México (id={mx_id})")
    else:
        cur.execute("SELECT id FROM paises WHERE codigo = 'MX'")
        mx_id = cur.fetchone()[0]
        print(f"  ⚠️  País México ya existe (id={mx_id})")

    cur.execute(
        "INSERT INTO paises (nombre, codigo) VALUES (%s, %s) ON CONFLICT (codigo) DO NOTHING RETURNING id",
        ("USA", "US"),
    )
    row = cur.fetchone()
    if row:
        us_id = row[0]
        print(f"  ✅ País: USA (id={us_id})")
    else:
        cur.execute("SELECT id FROM paises WHERE codigo = 'US'")
        us_id = cur.fetchone()[0]
        print(f"  ⚠️  País USA ya existe (id={us_id})")

    # 2. Regiones
    regiones = [
        (mx_id, "León, Gto", "LON"),
        (mx_id, "Irapuato, Gto", "IRA"),
        (us_id, "Pearland, TX", "PRL"),
        (us_id, "Houston, TX", "HOU"),
    ]
    for pais_id, nombre, codigo in regiones:
        cur.execute(
            """
            INSERT INTO regiones (pais_id, nombre, codigo)
            VALUES (%s, %s, %s)
            ON CONFLICT (pais_id, codigo) DO NOTHING
            RETURNING id
            """,
            (pais_id, nombre, codigo),
        )
        row = cur.fetchone()
        if row:
            print(f"  ✅ Región: {nombre} ({codigo}) id={row[0]}")
        else:
            print(f"  ⚠️  Región {codigo} ya existe, skip.")

    # 3. Admin user
    admin_email = "admin@vidaug.mx"
    admin_password = "changeme123"
    password_hash = _pwd_context.hash(admin_password)

    cur.execute(
        """
        INSERT INTO usuarios (nombre, email, password_hash, rol)
        VALUES (%s, %s, %s, 'admin')
        ON CONFLICT (email) DO NOTHING
        RETURNING id
        """,
        ("Admin VIDA UG", admin_email, password_hash),
    )
    row = cur.fetchone()
    if row:
        print(f"  ✅ Admin: {admin_email} (id={row[0]})")
        print(f"     🔑  Contraseña inicial: {admin_password}")
        print(f"     ⚠️  Cambia esta contraseña después de hacer login!")
    else:
        print(f"  ⚠️  Admin {admin_email} ya existe, skip.")

    conn.commit()
    cur.close()
    conn.close()
    print("\n✅ Seed completado.")


if __name__ == "__main__":
    seed()
