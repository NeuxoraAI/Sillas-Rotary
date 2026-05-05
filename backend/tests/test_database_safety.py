"""Guardrails to ensure tests never run against production-like databases."""

import pytest

from database import assert_test_database_target, build_test_conn_kwargs


def test_rejects_non_test_database_url() -> None:
    with pytest.raises(RuntimeError, match="refused"):
        assert_test_database_target(
            db_name="rotary_prod",
            db_host="db.supabase.co",
            test_database_url=None,
            test_schema=None,
        )


def test_allows_explicit_test_database_url() -> None:
    assert_test_database_target(
        db_name="rotary_prod",
        db_host="db.supabase.co",
        test_database_url="postgresql://user:pass@localhost:5432/rotary_test",
        test_schema=None,
    )


def test_allows_explicit_test_schema() -> None:
    assert_test_database_target(
        db_name="rotary_prod",
        db_host="db.supabase.co",
        test_database_url=None,
        test_schema="test_suite",
    )


def test_rejects_public_test_schema() -> None:
    with pytest.raises(RuntimeError, match="schema"):
        assert_test_database_target(
            db_name="rotary_prod",
            db_host="db.supabase.co",
            test_database_url=None,
            test_schema="public",
        )


def test_test_schema_search_path_has_no_public_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_HOST", "db.supabase.co")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("DB_NAME", "rotary_prod")
    monkeypatch.setenv("TEST_DB_SCHEMA", "test_suite")
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    conn_kwargs = build_test_conn_kwargs()

    assert conn_kwargs["options"] == "-c search_path=test_suite"
