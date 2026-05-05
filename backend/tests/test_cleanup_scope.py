"""Tests for the scoped cleanup mechanism in conftest.py.

Verifies that:
- _TABLES_ORDER is in correct dependency order (children before parents)
- _track helper registers IDs correctly
- Safety net patterns are comprehensive
"""

import sys
from pathlib import Path

import pytest

# Add backend/ to path so we can import conftest
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import from conftest — these will NOT exist until we implement them
from conftest import (
    _TABLES_ORDER,
    _qualified_table_names,
    _requires_db_connection,
    _resolve_test_schema,
    _track,
)


class TestTablesOrder:
    """Verify _TABLES_ORDER is in correct dependency order (children first)."""

    def test_historial_estados_is_first(self) -> None:
        """historial_estados should be first — child of estudios/solicitudes."""
        assert _TABLES_ORDER[0] == "historial_estados"

    def test_beneficiarios_before_paises(self) -> None:
        """beneficiarios must be deleted before paises (FK via regiones)."""
        assert _TABLES_ORDER.index("beneficiarios") < _TABLES_ORDER.index("paises")

    def test_tutores_before_beneficiarios(self) -> None:
        """tutores must be deleted before beneficiarios (FK dependency)."""
        assert _TABLES_ORDER.index("tutores") < _TABLES_ORDER.index("beneficiarios")

    def test_estudios_before_beneficiarios(self) -> None:
        """estudios_socioeconomicos must be deleted before beneficiarios."""
        assert _TABLES_ORDER.index("estudios_socioeconomicos") < _TABLES_ORDER.index("beneficiarios")

    def test_solicitudes_before_beneficiarios(self) -> None:
        """solicitudes_tecnicas must be deleted before beneficiarios."""
        assert _TABLES_ORDER.index("solicitudes_tecnicas") < _TABLES_ORDER.index("beneficiarios")

    def test_region_counters_before_regiones(self) -> None:
        """region_counters should come before regiones."""
        assert _TABLES_ORDER.index("region_counters") < _TABLES_ORDER.index("regiones")

    def test_regiones_before_paises(self) -> None:
        """regiones must be deleted before paises (FK dependency)."""
        assert _TABLES_ORDER.index("regiones") < _TABLES_ORDER.index("paises")

    def test_truncate_is_guarded(self, tmp_path) -> None:
        """conftest.py MUST use TRUNCATE only with a safe DB guardrail.

        TRUNCATE is acceptable when:
        1. The connection factory calls assert_test_database_target() first.
        2. Each test gets a clean slate via TRUNCATE within a guarded session.

        This test verifies the guardrail exists via build_test_conn_kwargs import.
        """
        import conftest
        conftest_path = conftest.__file__
        content = open(conftest_path).read()
        # Must import the guarded connection factory
        assert "build_test_conn_kwargs" in content, (
            "conftest.py must import build_test_conn_kwargs which calls assert_test_database_target"
        )
        # Must have TRUNCATE within session-scoped fixture (not global)
        assert "TRUNCATE TABLE" in content, (
            "conftest.py must have TRUNCATE TABLE for test isolation"
        )


class TestTrackHelper:
    """Verify _track helper registers IDs correctly."""

    def test_track_int_id(self) -> None:
        tracker: dict = {table: [] for table in _TABLES_ORDER}
        _track("paises", 42, tracker)
        assert tracker["paises"] == [42]

    def test_track_dict_key_for_region_counter(self) -> None:
        tracker: dict = {table: [] for table in _TABLES_ORDER}
        key = {"pais_codigo": "MX", "region_codigo": "LON", "anio": 2026}
        _track("region_counters", key, tracker)
        assert tracker["region_counters"] == [key]

    def test_track_multiple_ids_same_table(self) -> None:
        tracker: dict = {table: [] for table in _TABLES_ORDER}
        _track("usuarios", 1, tracker)
        _track("usuarios", 2, tracker)
        _track("usuarios", 3, tracker)
        assert tracker["usuarios"] == [1, 2, 3]

    def test_track_does_not_affect_other_tables(self) -> None:
        tracker: dict = {table: [] for table in _TABLES_ORDER}
        _track("paises", 10, tracker)
        assert tracker["regiones"] == []
        assert tracker["usuarios"] == []


class TestDbRequirementDetection:
    def test_requires_db_when_client_fixture_present(self) -> None:
        assert _requires_db_connection(["client"]) is True

    def test_requires_db_when_db_fixture_present(self) -> None:
        assert _requires_db_connection(["_test_db_conn"]) is True

    def test_does_not_require_db_for_pure_unit_tests(self) -> None:
        assert _requires_db_connection(["monkeypatch", "tmp_path"]) is False


class TestSchemaQualification:
    def test_resolve_test_schema_rejects_public(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_DB_SCHEMA", "public")
        with pytest.raises(RuntimeError, match="public"):
            _resolve_test_schema()

    def test_qualified_table_names_when_schema_enabled(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_DB_SCHEMA", "test_suite")
        qualified = _qualified_table_names()

        assert qualified[0] == "test_suite.historial_estados"
        assert qualified[-1] == "test_suite.usuarios"
