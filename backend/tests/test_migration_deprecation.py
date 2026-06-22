from collections import Counter
from pathlib import Path


def test_migrate_v2_marked_as_legacy_and_non_executable() -> None:
    migrate_file = Path(__file__).resolve().parents[1] / "migrate_v2.sql"
    content = migrate_file.read_text(encoding="utf-8")

    assert "LEGACY" in content
    assert "DO NOT EXECUTE" in content
    assert "RAISE EXCEPTION" in content


def test_incremental_migrations_readme_exists_with_rule() -> None:
    readme = Path(__file__).resolve().parents[1] / "migrations" / "README.md"
    content = readme.read_text(encoding="utf-8")

    assert "solo migraciones incrementales" in content.lower()
    assert "reversible" in content.lower()


def test_incremental_migration_prefixes_are_unique() -> None:
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    prefixes = [path.name.split("_", 1)[0] for path in migrations_dir.glob("*.sql")]
    duplicate_prefixes = [prefix for prefix, count in Counter(prefixes).items() if count > 1]

    assert duplicate_prefixes == []
