import pytest

from server.core.exceptions import WeakPasswordError
from server.core.password_policy import PasswordPolicy


def test_validate_accepts_strong_password():
    PasswordPolicy().validate("Password1")


def test_validate_rejects_too_short_password():
    with pytest.raises(WeakPasswordError, match="at least 8 characters"):
        PasswordPolicy().validate("Pass1")


def test_validate_rejects_password_without_uppercase():
    with pytest.raises(WeakPasswordError, match="uppercase letter"):
        PasswordPolicy().validate("password1")


def test_validate_rejects_password_without_number():
    with pytest.raises(WeakPasswordError, match="at least one number"):
        PasswordPolicy().validate("Password")


def test_min_length_constant():
    assert PasswordPolicy.MIN_LENGTH == 8
