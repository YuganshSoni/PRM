from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import LlmProvider, UserRole
from server.routers.config_router import ConfigRouter
from server.schemas.response_values import ConfigMessage
from server.schemas.responses.config import SystemConfigResponse


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(ConfigRouter().router)
    return application


def _admin():
    user = MagicMock()
    user.id = 1
    user.force_password_change = False
    user.role = SimpleNamespace(name=UserRole.ADMIN.value)
    return user


def _override(app: FastAPI, service):
    async def override_user():
        return _admin()

    async def override_service():
        return service

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    app.dependency_overrides[dependency_provider.get_system_config_service] = (
        override_service
    )


def test_get_config(app: FastAPI):
    service = AsyncMock()
    service.get_config.return_value = SystemConfigResponse(
        llm_provider=LlmProvider.GEMINI,
        llm_api_key_masked="****abcd",
        scheduler_interval_hours=6,
        max_weekly_hours=40,
        email_enabled=False,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="ops",
        smtp_password_masked="****",
        smtp_from_email="ops@example.com",
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _override(app, service)
    client = TestClient(app)

    response = client.get("/config")

    assert response.status_code == 200
    body = response.json()
    assert body["llm_provider"] == LlmProvider.GEMINI
    assert body["scheduler_interval_hours"] == 6
    service.get_config.assert_awaited_once()


def test_update_config(app: FastAPI):
    service = AsyncMock()
    service.update_config.return_value = None
    _override(app, service)
    client = TestClient(app)

    response = client.put(
        "/config",
        json={"scheduler_interval_hours": 12, "max_weekly_hours": 35},
    )

    assert response.status_code == 200
    assert response.json()["message"] == ConfigMessage.SETTINGS_UPDATED
    service.update_config.assert_awaited_once()
