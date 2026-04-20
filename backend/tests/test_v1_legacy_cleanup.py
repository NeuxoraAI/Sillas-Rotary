"""Tests for Phase 4: v1/v2 legacy cleanup.

Verifies that:
- init_db.py no longer creates the legacy `capturistas` table
- init_db.py DDL marks `capturista_id` columns as deprecated (commented)
- init_db.py DDL marks legacy indexes as deprecated (commented)
- README.md no longer references v1-only artifacts (/api/login, capturista_id in examples)
- README.md documents the v2 architecture (JWT, usuarios, Supabase)
- Routers use `usuario_id` consistently (no `capturista_id` in active code paths)
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Task 4.1 + 4.2: init_db.py legacy removal
# ---------------------------------------------------------------------------

def test_init_db_no_capturistas_table() -> None:
    """init_db.py must NOT create the legacy `capturistas` table."""
    content = (ROOT / "init_db.py").read_text(encoding="utf-8")
    assert "CREATE TABLE" in content
    # "capturistas" may appear in comments (DEPRECATED notes), but not in
    # active CREATE TABLE statements.
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "CREATE TABLE" in stripped and "capturistas" in stripped:
            raise AssertionError(
                "init_db.py still creates the legacy 'capturistas' table — remove it"
            )


def test_init_db_capturista_id_columns_deprecated() -> None:
    """capturista_id columns in DDL must be commented out (deprecated, not deleted)."""
    content = (ROOT / "init_db.py").read_text(encoding="utf-8")

    # Active (non-commented) capturista_id references must not exist.
    # Comments can be Python (#) or SQL (--) style.
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("--"):
            continue
        if "capturista_id" in stripped and "REFERENCES capturistas" in stripped:
            raise AssertionError(
                "init_db.py still has active capturista_id FK to capturistas — "
                "comment it out as deprecated"
            )


def test_init_db_legacy_indexes_deprecated() -> None:
    """Legacy indexes on capturista_id must be commented out."""
    content = (ROOT / "init_db.py").read_text(encoding="utf-8")

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("--"):
            continue
        if "idx_estudios_capturista" in stripped or "idx_solicitudes_capturista" in stripped:
            raise AssertionError(
                "init_db.py still creates legacy capturista indexes — "
                "comment them out as deprecated"
            )


# ---------------------------------------------------------------------------
# Task 4.1 + 4.2: README.md v1 references removed
# ---------------------------------------------------------------------------

def test_readme_no_api_login_endpoint() -> None:
    """README.md must not document the removed /api/login v1 endpoint."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    # The endpoint table must not list /api/login
    lines = content.splitlines()
    in_endpoint_table = False
    for line in lines:
        if "API" in line and "Endpoints" in line:
            in_endpoint_table = True
            continue
        if in_endpoint_table and line.strip() == "" or (in_endpoint_table and line.startswith("##")):
            in_endpoint_table = False
            continue
        if in_endpoint_table and "/api/login" in line:
            raise AssertionError(
                "README.md still documents /api/login v1 endpoint — "
                "replace with v2 /api/auth/login"
            )


def test_readme_no_capturista_id_in_examples() -> None:
    """README.md example payloads must not use capturista_id."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    # In code blocks, capturista_id should not appear
    in_code_block = False
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block and "capturista_id" in line:
            raise AssertionError(
                "README.md code example still uses capturista_id — "
                "update to v2 contract (usuario_id via JWT)"
            )


def test_readme_no_capturistas_table_in_schema() -> None:
    """README.md schema section must not list the capturistas table."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    in_schema_section = False
    for line in content.splitlines():
        if "Base de datos" in line:
            in_schema_section = True
            continue
        if in_schema_section and line.startswith("##"):
            in_schema_section = False
            continue
        if in_schema_section and line.strip() == "capturistas":
            raise AssertionError(
                "README.md schema section still lists 'capturistas' table — "
                "replace with 'usuarios'"
            )


def test_readme_documents_jwt_auth() -> None:
    """README.md must document JWT authentication (v2), not name-only login."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    assert "JWT" in content, "README.md must document JWT authentication"
    assert "usuarios" in content, "README.md must reference the usuarios table"


def test_readme_no_sqlite_as_primary_db() -> None:
    """README.md must not present SQLite as the primary database."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    # SQLite badge should not be present as a primary technology
    assert "SQLite-Dev" not in content, (
        "README.md still shows SQLite badge as primary DB — "
        "update to Supabase/PostgreSQL"
    )


# ---------------------------------------------------------------------------
# Task 4.1 + 4.2: Routers use usuario_id (no capturista_id in active code)
# ---------------------------------------------------------------------------

def test_socioeconomico_router_no_capturista_id_in_code() -> None:
    """socioeconomico.py must not reference capturista_id in active code."""
    content = (ROOT / "routers" / "socioeconomico.py").read_text(encoding="utf-8")

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "capturista_id" in stripped:
            raise AssertionError(
                "socioeconomico.py still references capturista_id in active code — "
                "use usuario.usuario_id instead"
            )


def test_tecnica_router_no_capturista_id_in_code() -> None:
    """tecnica.py must not reference capturista_id in active code."""
    content = (ROOT / "routers" / "tecnica.py").read_text(encoding="utf-8")

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "capturista_id" in stripped:
            raise AssertionError(
                "tecnica.py still references capturista_id in active code — "
                "use usuario.usuario_id instead"
            )


# ---------------------------------------------------------------------------
# Task 4.3: Regression — v2 critical endpoints still work
# ---------------------------------------------------------------------------

def test_readme_endpoints_table_has_v2_auth() -> None:
    """README.md endpoint table must include /api/auth/login."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    assert "/api/auth/login" in content, (
        "README.md must document the v2 /api/auth/login endpoint"
    )


def test_readme_endpoints_table_has_estudios() -> None:
    """README.md must document /api/estudios endpoints."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    assert "/api/estudios" in content, (
        "README.md must document /api/estudios endpoints"
    )


def test_readme_endpoints_table_has_solicitudes() -> None:
    """README.md must document /api/solicitudes endpoints."""
    content = (ROOT.parent / "README.md").read_text(encoding="utf-8")

    assert "/api/solicitudes" in content, (
        "README.md must document /api/solicitudes endpoints"
    )
