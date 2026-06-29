from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import UserRole
from server.routers.auth_router import AuthRouter
from server.schemas.response_values import AuthMessage, TokenType
from server.services.auth_service import ChangePasswordResult, LoginResult


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(AuthRouter().router)
    return application


def _user(*, role: UserRole = UserRole.MANAGER, force: bool = False):
    user = MagicMock()
    user.id = 1
    user.username = "alice"
    user.full_name = "Alice"
    user.force_password_change = force
    user.role = SimpleNamespace(name=role.value)
    return user


def test_login(app: FastAPI):
    auth_service = AsyncMock()
    user = _user(force=True)
    auth_service.login.return_value = LoginResult(
        access_token="tok-1", user=user
    )

    async def override_auth():
        return auth_service

    app.dependency_overrides[dependency_provider.get_auth_service] = override_auth
    client = TestClient(app)

    response = client.post(
        "/auth/login", json={"username": "alice", "password": "Secret1!"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "tok-1"
    assert body["token_type"] == TokenType.BEARER
    assert body["role"] == UserRole.MANAGER
    assert body["force_password_change"] is True
    assert body["full_name"] == "Alice"
    auth_service.login.assert_awaited_once_with("alice", "Secret1!")


def test_change_password(app: FastAPI):
    user = _user(force=True)
    updated = _user(force=False)
    auth_service = AsyncMock()
    auth_service.change_password.return_value = ChangePasswordResult(
        access_token="tok-2", user=updated
    )

    async def override_auth():
        return auth_service

    async def override_user():
        return user

    app.dependency_overrides[dependency_provider.get_auth_service] = override_auth
    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    client = TestClient(app)

    response = client.post(
        "/auth/change-password",
        json={"new_password": "NewPass1!", "confirm_password": "NewPass1!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "tok-2"
    assert body["message"] == AuthMessage.PASSWORD_UPDATED
    assert body["force_password_change"] is False
    auth_service.change_password.assert_awaited_once_with(
        user, "NewPass1!", "NewPass1!"
    )


def test_logout(app: FastAPI):
    async def override_user():
        return _user()

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    client = TestClient(app)

    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == AuthMessage.LOGOUT_SUCCESS


def test_me(app: FastAPI):
    user = _user(role=UserRole.RESOURCE, force=True)

    async def override_user():
        return user

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    client = TestClient(app)

    response = client.get("/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["username"] == "alice"
    assert body["role"] == UserRole.RESOURCE
    assert body["force_password_change"] is True
