"""Integration tests for vista_tecnicos enriched endpoint.

Requires a real PostgreSQL test database configured via TEST_DATABASE_URL
or TEST_DB_SCHEMA. Skipped automatically when no test DB is available.
"""

import pytest


def _get_token(client, email: str, password: str) -> str:
    """Helper to login and get JWT token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def _create_pais(_test_db_conn, nombre: str, codigo: str) -> dict:
    with _test_db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO paises (nombre, codigo) VALUES (%s, %s) RETURNING *",
            (nombre, codigo),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


def _create_region(_test_db_conn, pais_id: int, nombre: str, codigo: str) -> dict:
    with _test_db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO regiones (pais_id, nombre, codigo) VALUES (%s, %s, %s) RETURNING *",
            (pais_id, nombre, codigo),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


def _create_beneficiario(
    _test_db_conn,
    *,
    nombre: str,
    region_id: int | None = None,
    ciudad: str | None = None,
    diagnostico: str | None = None,
    telefonos: str | None = None,
) -> dict:
    with _test_db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO beneficiarios (nombre, region_id, ciudad, diagnostico, telefonos)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
            """,
            (nombre, region_id, ciudad, diagnostico, telefonos),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


def _create_estudio(_test_db_conn, beneficiario_id: int, usuario_id: int, sede: str) -> dict:
    with _test_db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO estudios_socioeconomicos
                (beneficiario_id, usuario_id, sede, status)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (beneficiario_id, usuario_id, sede, "completo"),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


def _create_solicitud_tecnica(
    _test_db_conn,
    beneficiario_id: int,
    usuario_id: int,
    *,
    peso_kg: float | None = None,
    altura_total_in: float | None = None,
    foto_url: str | None = None,
) -> dict:
    with _test_db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO solicitudes_tecnicas
                (beneficiario_id, usuario_id, entorno, control_tronco, control_cabeza,
                 peso_kg, altura_total_in, foto_url, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (beneficiario_id, usuario_id, "Urbano", "Completo", "Independiente",
             peso_kg, altura_total_in, foto_url, "completo"),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


def _create_user(conn, nombre: str, email: str, password: str, rol: str) -> dict:
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    pw_hash = pwd.hash(password)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING *",
            (nombre, email, pw_hash, rol),
        )
        row = dict(cur.fetchone())
    conn.commit()
    return row


# ── Task 3.7: Integration test — combined filters ─────────────────────────────

@pytest.mark.integration
def test_listar_beneficiarios_with_pais_and_region_filters(
    client, _test_db_conn, tecnico_user, tecnico_headers
):
    """GIVEN pais_id + region_id filter WHEN GET /api/tecnica/beneficiarios THEN correct subset returned."""
    pais = _create_pais(_test_db_conn, "México", "MX")
    region_a = _create_region(_test_db_conn, pais["id"], "León", "LON")
    region_b = _create_region(_test_db_conn, pais["id"], "Irapuato", "IRA")

    # Ben in region_a
    b1 = _create_beneficiario(_test_db_conn, nombre="Ana López",
                               region_id=region_a["id"], ciudad="León")
    # Ben in region_b
    b2 = _create_beneficiario(_test_db_conn, nombre="Luis Pérez",
                               region_id=region_b["id"], ciudad="Irapuato")

    _create_estudio(_test_db_conn, b1["id"], tecnico_user["id"], "Sede León")
    _create_estudio(_test_db_conn, b2["id"], tecnico_user["id"], "Sede Irapuato")

    # Filter by region
    res = client.get(
        f"/api/tecnica/beneficiarios?region_id={region_a['id']}",
        headers=tecnico_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["nombre"] == "Ana López"

    # Filter by pais
    res = client.get(
        f"/api/tecnica/beneficiarios?pais_id={pais['id']}",
        headers=tecnico_headers,
    )
    assert res.status_code == 200
    assert res.json()["total"] == 2


# ── Task 3.8: Integration test — empty result ─────────────────────────────────

@pytest.mark.integration
def test_empty_result(client, _test_db_conn, tecnico_user, tecnico_headers):
    """GIVEN no matching beneficiaries WHEN GET /api/tecnica/beneficiarios THEN empty response shape."""
    res = client.get(
        "/api/tecnica/beneficiarios?q=NONEXISTENT_ZZZ",
        headers=tecnico_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20


# ── Additional: filter combinations ───────────────────────────────────────────

@pytest.mark.integration
def test_peso_range_filter(client, _test_db_conn, tecnico_user, tecnico_headers):
    """GIVEN peso_kg_min=55&peso_kg_max=75 WHEN listed THEN only matching returned."""
    pais = _create_pais(_test_db_conn, "MX", "MX")
    region = _create_region(_test_db_conn, pais["id"], "Centro", "CEN")

    b1 = _create_beneficiario(_test_db_conn, nombre="Peso60",
                               region_id=region["id"])
    b2 = _create_beneficiario(_test_db_conn, nombre="Peso80",
                               region_id=region["id"])

    _create_estudio(_test_db_conn, b1["id"], tecnico_user["id"], "Sede A")
    _create_estudio(_test_db_conn, b2["id"], tecnico_user["id"], "Sede B")
    _create_solicitud_tecnica(_test_db_conn, b1["id"], tecnico_user["id"], peso_kg=60.0)
    _create_solicitud_tecnica(_test_db_conn, b2["id"], tecnico_user["id"], peso_kg=80.0)

    res = client.get(
        "/api/tecnica/beneficiarios?peso_kg_min=55&peso_kg_max=75",
        headers=tecnico_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["peso_kg"] == 60.0


@pytest.mark.integration
def test_tiene_foto_filter(client, _test_db_conn, tecnico_user, tecnico_headers):
    """GIVEN tiene_foto=true WHEN listed THEN only beneficiaries with foto returned."""
    pais = _create_pais(_test_db_conn, "MX", "MX")
    region = _create_region(_test_db_conn, pais["id"], "Norte", "NTE")

    b1 = _create_beneficiario(_test_db_conn, nombre="ConFoto",
                               region_id=region["id"])
    b2 = _create_beneficiario(_test_db_conn, nombre="SinFoto",
                               region_id=region["id"])

    _create_estudio(_test_db_conn, b1["id"], tecnico_user["id"], "Sede X")
    _create_estudio(_test_db_conn, b2["id"], tecnico_user["id"], "Sede Y")
    _create_solicitud_tecnica(_test_db_conn, b1["id"], tecnico_user["id"],
                               foto_url="storage://fotos-tecnica/uuid.jpg")
    _create_solicitud_tecnica(_test_db_conn, b2["id"], tecnico_user["id"])

    res = client.get(
        "/api/tecnica/beneficiarios?tiene_foto=true",
        headers=tecnico_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["nombre"] == "ConFoto"
