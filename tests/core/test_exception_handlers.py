from unittest.mock import MagicMock

import pytest
from fastapi.responses import JSONResponse

from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.core.exceptions import (
    ConflictError,
    DatabaseUnavailableError,
    DuplicateTimesheetProjectError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    LlmInvocationError,
    LlmNotConfiguredError,
    NotFoundError,
    NotProjectOwnerError,
    OverAllocationError,
    PrmError,
    ResourceStatusNotFoundError,
    UserNotFoundError,
    ValidationError,
    WeakPasswordError,
)


@pytest.fixture
def registrar() -> ExceptionHandlerRegistrar:
    return ExceptionHandlerRegistrar()


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (WeakPasswordError("weak"), 400),
        (ValidationError("bad"), 400),
        (OverAllocationError("over"), 400),
        (DuplicateTimesheetProjectError("dup project"), 400),
        (InvalidCredentialsError("nope"), 401),
        (NotProjectOwnerError("not owner"), 403),
        (UserNotFoundError("missing"), 404),
        (NotFoundError("gone"), 404),
        (ConflictError("conflict"), 409),
        (DuplicateUsernameError("taken"), 409),
        (DatabaseUnavailableError("db down"), 503),
        (LlmNotConfiguredError("no key"), 503),
        (LlmInvocationError("llm fail"), 502),
        (ResourceStatusNotFoundError("status"), 500),
    ],
)
def test_status_for_maps_known_exceptions(registrar, exc, expected_status):
    assert registrar.status_for(exc) == expected_status


def test_status_for_unknown_prm_error_defaults_to_500(registrar):
    class WeirdError(PrmError):
        pass

    assert registrar.status_for(WeirdError("weird")) == 500


def test_subclass_matches_more_specific_entry_before_base(registrar):
    # DuplicateUsernameError is ConflictError; STATUS_MAP lists both — first match wins
    # by iteration order. Ensure duplicate username still resolves (not crash).
    status = registrar.status_for(DuplicateUsernameError("taken"))
    assert status in (409,)


@pytest.mark.asyncio
async def test_handle_prm_error_returns_json_body(registrar):
    request = MagicMock()
    exc = UserNotFoundError("User not found")
    response = await registrar.handle_prm_error(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert response.body
    # JSONResponse stores content; decode via body
    import json

    payload = json.loads(response.body.decode())
    assert payload["detail"] == "User not found"
    assert payload["code"] == "UserNotFoundError"


@pytest.mark.asyncio
async def test_handle_unhandled_returns_internal_error(registrar):
    request = MagicMock()
    response = await registrar.handle_unhandled(request, RuntimeError("boom"))

    assert response.status_code == 500
    import json

    payload = json.loads(response.body.decode())
    assert payload["detail"] == "Internal server error"
