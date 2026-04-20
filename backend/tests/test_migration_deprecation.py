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
