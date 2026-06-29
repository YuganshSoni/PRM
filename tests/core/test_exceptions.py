from server.core.exceptions import (
    ConflictError,
    DuplicateUsernameError,
    NotFoundError,
    OverAllocationError,
    PrmError,
    UserNotFoundError,
    ValidationError,
)


def test_prm_error_defaults_code_to_class_name():
    err = PrmError("something broke")
    assert err.message == "something broke"
    assert err.code == "PrmError"
    assert str(err) == "something broke"


def test_prm_error_accepts_explicit_code():
    err = PrmError("blocked", code="CustomCode")
    assert err.code == "CustomCode"
    assert err.message == "blocked"


def test_hierarchy_inheritance():
    assert issubclass(NotFoundError, PrmError)
    assert issubclass(ConflictError, PrmError)
    assert issubclass(ValidationError, PrmError)
    assert issubclass(UserNotFoundError, PrmError)
    assert issubclass(DuplicateUsernameError, ConflictError)
    assert issubclass(OverAllocationError, ValidationError)


def test_subclass_default_code_is_subclass_name():
    err = UserNotFoundError("User not found")
    assert err.code == "UserNotFoundError"
    assert isinstance(err, PrmError)


def test_isinstance_checks_used_by_status_map():
    assert isinstance(DuplicateUsernameError("dup"), ConflictError)
    assert isinstance(OverAllocationError("over"), ValidationError)
    assert isinstance(UserNotFoundError("missing"), PrmError)
