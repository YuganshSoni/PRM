from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import ProficiencyLevel, UserRole
from server.routers.skill_router import SkillRouter
from server.schemas.response_values import SkillMessage


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(SkillRouter().router)
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
    app.dependency_overrides[dependency_provider.get_skill_service] = override_service


def test_update_proficiency(app: FastAPI):
    service = AsyncMock()
    skill = MagicMock()
    skill.id = 9
    service.update_proficiency.return_value = skill
    _override(app, service)
    client = TestClient(app)

    response = client.put(
        "/skills/9",
        json={"proficiency_level": ProficiencyLevel.ADVANCED},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 9
    assert body["message"] == SkillMessage.SKILL_UPDATED
    service.update_proficiency.assert_awaited_once()
    assert service.update_proficiency.await_args.args[0] == 9


def test_remove_skill(app: FastAPI):
    service = AsyncMock()
    service.remove_skill.return_value = None
    _override(app, service)
    client = TestClient(app)

    response = client.delete("/skills/9")

    assert response.status_code == 204
    service.remove_skill.assert_awaited_once_with(9)
