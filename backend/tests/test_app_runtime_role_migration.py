from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0014_app_runtime_role.sql"
)


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def _statements() -> str:
    """SQL with `--` comment lines stripped, so assertions ignore prose."""
    lines = [
        ln for ln in _sql().splitlines() if not ln.lstrip().startswith("--")
    ]
    return "\n".join(lines)


def test_role_is_least_privilege_not_superuser() -> None:
    sql = _sql()
    assert "create role app_runtime login" in sql
    for attr in ("nosuperuser", "nocreatedb", "nocreaterole", "nobypassrls"):
        assert attr in sql, f"missing role attribute: {attr}"


def test_grants_dml_only_no_ddl() -> None:
    sql = _statements()
    assert "grant select, insert, update, delete on all tables in schema public to app_runtime" in sql
    assert "grant usage, select on all sequences in schema public to app_runtime" in sql
    # No blanket / DDL-capable grants reach the runtime role.
    assert "grant all" not in sql
    assert "truncate" not in sql  # TRUNCATE is intentionally withheld.


def test_permissive_policy_keeps_nobypassrls_role_functional() -> None:
    sql = _sql()
    # RLS is already enabled on every table; a permissive policy is required or
    # the NOBYPASSRLS role would be denied every row.
    assert "app_runtime_all" in sql
    assert "for all to app_runtime using (true) with check (true)" in sql


def test_future_tables_inherit_grants_via_default_privileges() -> None:
    sql = _sql()
    assert "alter default privileges for role postgres in schema public" in sql
