"""Tests for the scoped cleanup mechanism in conftest.py.

Verifies that:
- _TABLES_ORDER is in correct dependency order (children before parents)
- _track helper registers IDs correctly
- Safety net patterns are comprehensive
"""

import sys
from pathlib import Path

# Add backend/ to path so we can import conftest
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import from conftest — these will NOT exist until we implement them
from conftest import _TABLES_ORDER, _track


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

    def test_no_truncate_in_file(self, tmp_path) -> None:
        """conftest.py must NOT contain global TRUNCATE CASCADE."""
        import conftest
        conftest_path = conftest.__file__
        content = open(conftest_path).read()
        assert "TRUNCATE TABLE" not in content, (
            "conftest.py still uses TRUNCATE TABLE — replace with scoped cleanup"
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
