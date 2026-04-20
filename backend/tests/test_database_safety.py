"""Guardrails to ensure tests never run against production-like databases."""

import pytest

from database import assert_test_database_target


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
