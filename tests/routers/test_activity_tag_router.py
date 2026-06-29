from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import UserRole
from server.routers.activity_tag_router import ActivityTagRouter
from server.schemas.responses.activity_tag import (
    ActivityTagListResponse,
    ActivityTagResponse,
)


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(ActivityTagRouter().router)
    return application


def _resource_user():
    user = MagicMock()
    user.id = 5
    user.force_password_change = False
    user.role = SimpleNamespace(name=UserRole.RESOURCE.value)
    return user


def test_list_activity_tags(app: FastAPI):
    service = AsyncMock()
    service.list_predefined_tags.return_value = ActivityTagListResponse(
        items=[
            ActivityTagResponse(id=1, name="Development", display_order=1),
            ActivityTagResponse(id=2, name="Meeting", display_order=2),
        ]
    )

    async def override_user():
        return _resource_user()

    async def override_service():
        return service

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    app.dependency_overrides[dependency_provider.get_activity_tag_service] = (
        override_service
    )
    client = TestClient(app)

    response = client.get("/activity-tags")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["name"] == "Development"
    service.list_predefined_tags.assert_awaited_once()
