from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import MilestoneStatus, UserRole
from server.routers.milestone_router import MilestoneRouter
from server.schemas.response_values import MilestoneMessage
from server.schemas.responses.milestone import StoryPointSummary


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(MilestoneRouter().router)
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
    app.dependency_overrides[dependency_provider.get_milestone_service] = (
        override_service
    )


def _milestone(**overrides):
    base = dict(
        id=3,
        title="Ship MVP",
        due_date=date(2026, 8, 1),
        story_points=5,
        status=MilestoneStatus.NOT_STARTED,
        sort_order=1,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_add_milestone(app: FastAPI):
    service = AsyncMock()
    service.add_milestone.return_value = _milestone()
    _override(app, service)
    client = TestClient(app)

    response = client.post(
        "/projects/7/milestones",
        json={
            "title": "Ship MVP",
            "due_date": "2026-08-01",
            "story_points": 5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Ship MVP"
    assert body["status"] == MilestoneStatus.NOT_STARTED
    service.add_milestone.assert_awaited_once()
    assert service.add_milestone.await_args.args[0] == 7


def test_list_milestones(app: FastAPI):
    service = AsyncMock()
    service.list_milestones.return_value = (
        [_milestone()],
        StoryPointSummary(total=10, completed=5, remaining=5),
    )
    _override(app, service)
    client = TestClient(app)

    response = client.get("/projects/7/milestones")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["story_point_summary"]["remaining"] == 5
    service.list_milestones.assert_awaited_once_with(7)


def test_update_milestone_status(app: FastAPI):
    service = AsyncMock()
    service.update_milestone_status.return_value = _milestone(
        status=MilestoneStatus.DONE
    )
    _override(app, service)
    client = TestClient(app)

    response = client.put(
        "/milestones/3",
        json={"status": MilestoneStatus.DONE},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == MilestoneStatus.DONE
    assert body["message"] == MilestoneMessage.MILESTONE_UPDATED
    service.update_milestone_status.assert_awaited_once_with(
        3, MilestoneStatus.DONE
    )
