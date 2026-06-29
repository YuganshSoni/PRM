from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import UserRole, UserStatus
from server.routers.user_router import UserRouter
from server.schemas.response_values import UserMessage
from server.services.user_service import UserListResult


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(UserRouter().router)
    return application


def _admin():
    user = MagicMock()
    user.id = 99
    user.force_password_change = False
    user.role = SimpleNamespace(name=UserRole.ADMIN.value)
    return user


def _bind(app: FastAPI, service, admin=None):
    actor = admin or _admin()

    async def override_user():
        return actor

    async def override_service():
        return service

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    app.dependency_overrides[dependency_provider.get_user_service] = override_service
    return actor


def _user_row(**overrides):
    base = dict(
        id=5,
        username="ada",
        email="ada@example.com",
        full_name="Ada Lovelace",
        role=SimpleNamespace(name=UserRole.RESOURCE.value),
        status=UserStatus.ACTIVE,
        force_password_change=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_create_user(app: FastAPI):
    service = AsyncMock()
    service.create_user.return_value = _user_row()
    _bind(app, service)
    client = TestClient(app)

    response = client.post(
        "/users",
        json={
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "username": "ada",
            "temporary_password": "TempPass1!",
            "role": UserRole.RESOURCE,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "ada"
    assert body["message"] == UserMessage.ACCOUNT_CREATED
    service.create_user.assert_awaited_once()


def test_list_users(app: FastAPI):
    service = AsyncMock()
    service.list_users.return_value = UserListResult(
        items=[_user_row()],
        total=1,
        active_count=1,
        inactive_count=0,
    )
    _bind(app, service)
    client = TestClient(app)

    response = client.get("/users")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Ada Lovelace"


def test_lookup_user(app: FastAPI):
    service = AsyncMock()
    service.lookup_user.return_value = _user_row()
    _bind(app, service)
    client = TestClient(app)

    response = client.get("/users/lookup?identifier=ada")

    assert response.status_code == 200
    assert response.json()["username"] == "ada"
    service.lookup_user.assert_awaited_once_with("ada")


def test_get_user(app: FastAPI):
    service = AsyncMock()
    service.get_user.return_value = _user_row()
    _bind(app, service)
    client = TestClient(app)

    response = client.get("/users/5")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["force_password_change"] is True


def test_reset_password(app: FastAPI):
    service = AsyncMock()
    service.reset_password.return_value = None
    admin = _bind(app, service)
    client = TestClient(app)

    response = client.post(
        "/users/5/reset-password",
        json={"temporary_password": "NewTemp1!"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == UserMessage.PASSWORD_RESET
    service.reset_password.assert_awaited_once_with(5, "NewTemp1!", admin.id)


def test_deactivate_and_reactivate(app: FastAPI):
    service = AsyncMock()
    service.deactivate.return_value = None
    service.reactivate.return_value = None
    admin = _bind(app, service)
    client = TestClient(app)

    deactivated = client.post("/users/5/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["message"] == UserMessage.USER_DEACTIVATED
    service.deactivate.assert_awaited_once_with(5, admin.id)

    reactivated = client.post("/users/5/reactivate")
    assert reactivated.status_code == 200
    assert reactivated.json()["message"] == UserMessage.USER_REACTIVATED
    service.reactivate.assert_awaited_once_with(5, admin.id)
