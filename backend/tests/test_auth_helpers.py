"""Unit tests for reusable RBAC helpers in auth router."""

import pytest
from fastapi import HTTPException

from routers.auth import CurrentUser, assert_resource_owner, require_roles


def _user(role: str, user_id: int = 10) -> CurrentUser:
    return CurrentUser(
        usuario_id=user_id,
        nombre="Test",
        email="test@example.com",
        rol=role,
    )


def test_require_roles_allows_configured_role() -> None:
    checker = require_roles("admin", "tecnico")
    current = _user("tecnico")

    assert checker(current) == current


def test_require_roles_rejects_unconfigured_role() -> None:
    checker = require_roles("admin")

    with pytest.raises(HTTPException) as exc:
        checker(_user("capturista"))

    assert exc.value.status_code == 403


def test_assert_resource_owner_allows_owner() -> None:
    assert_resource_owner(row_user_id=15, user=_user("capturista", user_id=15))


def test_assert_resource_owner_allows_admin() -> None:
    assert_resource_owner(row_user_id=15, user=_user("admin", user_id=99))


def test_assert_resource_owner_rejects_non_owner_non_admin() -> None:
    with pytest.raises(HTTPException) as exc:
        assert_resource_owner(row_user_id=15, user=_user("tecnico", user_id=18))

    assert exc.value.status_code == 403
