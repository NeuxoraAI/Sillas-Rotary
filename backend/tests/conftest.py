"""
Test fixtures for Sillas Rotary v2 API.

Strategy:
- Uses a real PostgreSQL test database (same Supabase project, separate test schema
  OR the main DB with TRUNCATE per test — configure via TEST_* env vars).
- Overrides FastAPI's get_db dependency with a test connection via
  app.dependency_overrides[get_db].
- Each test gets a clean DB state via autouse TRUNCATE fixture.
"""

import os

# Inject a test JWT secret BEFORE importing the app. Production code fails
# fast if JWT_SECRET is missing or weak; tests need a deterministic strong
# value that is never used outside the test process.
os.environ.setdefault(
    "JWT_SECRET",
    "test-secret-" + ("x" * 32),
)

import pytest
import psycopg2
import psycopg2.extras
from fastapi.testclient import TestClient
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Re-use the same env vars as production. Point to a test Supabase DB or
# set TEST_DB_* vars to isolate. For CI, ensure TRUNCATE is safe.
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Test DB connection factory
# ---------------------------------------------------------------------------

def _make_test_conn():
    """Create a psycopg2 connection for tests using environment variables."""
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )


# ---------------------------------------------------------------------------
# DB adapter for test fixture
# ---------------------------------------------------------------------------

class _TestDBAdapter:
    """Test adapter wrapping a real psycopg2 cursor (auto-commit mode)."""

    def __init__(self, cursor) -> None:
        self._cur = cursor

    def execute(self, sql: str, params: tuple = ()) -> "_TestDBAdapter":
        self._cur.execute(sql, params)
        return self

    def fetchone(self) -> dict | None:
        return self._cur.fetchone()

    def fetchall(self) -> list[dict]:
        return self._cur.fetchall()


# ---------------------------------------------------------------------------
# Session-scoped connection (shared across all tests for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _test_db_conn():
    """Single PostgreSQL connection for the entire test session."""
    conn = _make_test_conn()
    conn.autocommit = False
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Important: override FastAPI dependency BEFORE importing app
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def override_db(_test_db_conn):
    """
    Override FastAPI's get_db dependency with a test adapter backed by
    the shared test connection. This means all routes use the test DB.
    """
    from main import app
    from database import get_db

    cur = _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    adapter = _TestDBAdapter(cur)

    def _test_get_db():
        yield adapter

    app.dependency_overrides[get_db] = _test_get_db
    yield
    app.dependency_overrides.clear()
    cur.close()


# ---------------------------------------------------------------------------
# Clean DB state per test (autouse TRUNCATE)
# ---------------------------------------------------------------------------

_TABLES_ORDER = [
    "historial_estados",
    "solicitudes_tecnicas",
    "estudios_socioeconomicos",
    "tutores",
    "beneficiarios",
    "region_counters",
    "regiones",
    "paises",
    "usuarios",
]


@pytest.fixture(autouse=True)
def clean_db(_test_db_conn):
    """Truncate all tables before each test for isolation."""
    with _test_db_conn.cursor() as cur:
        tables = ", ".join(_TABLES_ORDER)
        cur.execute(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
    _test_db_conn.commit()
    yield
    _test_db_conn.rollback()


# ---------------------------------------------------------------------------
# TestClient
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client(_test_db_conn, override_db):
    """FastAPI TestClient using the test database override."""
    from main import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Seed fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pais_mx(_test_db_conn) -> dict:
    """Insert pais México and return its data."""
    with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO paises (nombre, codigo) VALUES (%s, %s) RETURNING *",
            ("México", "MX"),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


@pytest.fixture
def pais_us(_test_db_conn) -> dict:
    """Insert pais USA and return its data."""
    with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO paises (nombre, codigo) VALUES (%s, %s) RETURNING *",
            ("USA", "US"),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


@pytest.fixture
def region_lon(pais_mx, _test_db_conn) -> dict:
    """Insert region León (MX/LON) and return its data."""
    with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO regiones (pais_id, nombre, codigo) VALUES (%s, %s, %s) RETURNING *",
            (pais_mx["id"], "León, Gto", "LON"),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


@pytest.fixture
def region_ira(pais_mx, _test_db_conn) -> dict:
    """Insert region Irapuato (MX/IRA) and return its data."""
    with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO regiones (pais_id, nombre, codigo) VALUES (%s, %s, %s) RETURNING *",
            (pais_mx["id"], "Irapuato, Gto", "IRA"),
        )
        row = dict(cur.fetchone())
    _test_db_conn.commit()
    return row


def _create_user(conn, nombre: str, email: str, password: str, rol: str) -> dict:
    """Helper to insert a user with a hashed password."""
    password_hash = _pwd_context.hash(password)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO usuarios (nombre, email, password_hash, rol)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (nombre, email, password_hash, rol),
        )
        row = dict(cur.fetchone())
    conn.commit()
    return row


@pytest.fixture
def admin_user(_test_db_conn) -> dict:
    """Create an admin user. Returns DB row (no password exposed)."""
    return _create_user(
        _test_db_conn,
        nombre="Admin Test",
        email="admin@test.mx",
        password="adminpass123",
        rol="admin",
    )


@pytest.fixture
def capturista_user(_test_db_conn) -> dict:
    """Create a capturista user."""
    return _create_user(
        _test_db_conn,
        nombre="Capturista Test",
        email="cap@test.mx",
        password="cappass123",
        rol="capturista",
    )


@pytest.fixture
def tecnico_user(_test_db_conn) -> dict:
    """Create a técnico user."""
    return _create_user(
        _test_db_conn,
        nombre="Técnico Test",
        email="tec@test.mx",
        password="tecpass123",
        rol="tecnico",
    )


def _get_token(client, email: str, password: str) -> str:
    """Helper to login and get JWT token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture
def admin_headers(client, admin_user) -> dict:
    """Authorization headers for admin user."""
    token = _get_token(client, "admin@test.mx", "adminpass123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def capturista_headers(client, capturista_user) -> dict:
    """Authorization headers for capturista user."""
    token = _get_token(client, "cap@test.mx", "cappass123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tecnico_headers(client, tecnico_user) -> dict:
    """Authorization headers for técnico user."""
    token = _get_token(client, "tec@test.mx", "tecpass123")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Sample registration fixtures (for socioeconomico + tecnica tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_estudio(client, capturista_user, region_lon, pais_mx) -> dict:
    """Create a sample completed estudio socioeconómico."""
    token = _get_token(client, "cap@test.mx", "cappass123")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "region_id": region_lon["id"],
        "sede": "León sede Forum",
        "beneficiario": {
            "nombre": "Beneficiario Test",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "telefonos": "4621234567",
        },
        "tutores": [
            {
                "numero_tutor": 1,
                "nombre": "Tutor Test",
                "edad": 45,
                "nivel_estudios": "Licenciatura",
                "estado_civil": "Casado",
                "num_hijos": 2,
                "vivienda": "Propia",
                "fuente_empleo": "Empleado",
                "antiguedad": "10 años",
                "ingreso_mensual": 12000.0,
                "tiene_imss": True,
                "tiene_infonavit": False,
            }
        ],
        "estudio": {
            "otras_fuentes_ingreso": "Ninguna",
            "monto_otras_fuentes": None,
            "tuvo_silla_previa": False,
            "como_obtuvo_silla": None,
            "elaboro_estudio": "Capturista Test",
            "fecha_estudio": "2026-04-18",
            "status": "completo",
        },
    }
    res = client.post("/api/estudios", json=payload, headers=headers)
    assert res.status_code == 201, f"sample_estudio failed: {res.text}"
    return res.json()