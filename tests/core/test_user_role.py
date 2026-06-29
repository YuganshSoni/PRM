from unittest.mock import MagicMock

import pytest

from server.core.user_role import user_role_enum, user_role_name
from server.models.enums import UserRole


def _user_with_role(role_name: str) -> MagicMock:
    user = MagicMock()
    user.role.name = role_name
    return user


def test_user_role_name_returns_role_name():
    assert user_role_name(_user_with_role("ADMIN")) == "ADMIN"
    assert user_role_name(_user_with_role("MANAGER")) == "MANAGER"
    assert user_role_name(_user_with_role("RESOURCE")) == "RESOURCE"


def test_user_role_enum_returns_matching_enum():
    assert user_role_enum(_user_with_role("ADMIN")) is UserRole.ADMIN
    assert user_role_enum(_user_with_role("MANAGER")) is UserRole.MANAGER
    assert user_role_enum(_user_with_role("RESOURCE")) is UserRole.RESOURCE


def test_user_role_enum_rejects_unknown_role():
    with pytest.raises(ValueError):
        user_role_enum(_user_with_role("UNKNOWN"))
