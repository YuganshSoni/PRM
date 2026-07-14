from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import HealthStatus, MilestoneStatus, ProjectStatus, UserRole
from server.routers.project_router import ProjectRouter
from server.schemas.response_values import ProjectMessage
from server.services.project_health_service import RiskFlagView
from server.services.project_service import (
    ManagedProjectListResult,
    ManagedProjectSummaryRow,
    ManagerAllocationRow,
    ManagerMilestoneRow,
    ManagerProjectDetailResult,
    ProjectListResult,
)


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(ProjectRouter().router)
    return application


def _user(role: UserRole):
    user = MagicMock()
    user.id = 1
    user.force_password_change = False
    user.role = SimpleNamespace(name=role.value)
    return user


def _bind(app: FastAPI, user, service):
    async def override_user():
        return user

    async def override_service():
        return service

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    app.dependency_overrides[dependency_provider.get_project_service] = override_service


def _project(**overrides):
    manager = MagicMock()
    manager.user = SimpleNamespace(full_name="Mgr One")
    base = dict(
        id=7,
        name="Apollo",
        description="Moon shot",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=ProjectStatus.ACTIVE,
        manager_id=4,
        manager=manager,
        total_story_points=20,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_create_project(app: FastAPI):
    service = AsyncMock()
    service.create_project.return_value = _project()
    _bind(app, _user(UserRole.ADMIN), service)
    client = TestClient(app)

    response = client.post(
        "/projects",
        json={
            "name": "Apollo",
            "description": "Moon shot",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": ProjectStatus.ACTIVE,
            "manager_id": 4,
            "total_story_points": 20,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 7
    assert body["message"] == ProjectMessage.PROJECT_CREATED
    service.create_project.assert_awaited_once()


def test_list_projects(app: FastAPI):
    service = AsyncMock()
    service.list_projects.return_value = ProjectListResult(
        items=[_project()], total=1
    )
    service.story_points_done.return_value = 8
    _bind(app, _user(UserRole.ADMIN), service)
    client = TestClient(app)

    response = client.get("/projects")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["manager_name"] == "Mgr One"
    assert body["items"][0]["story_points_done"] == 8
    service.story_points_done.assert_awaited_once_with(7)


def test_list_managed_projects(app: FastAPI):
    service = AsyncMock()
    service.list_by_manager.return_value = ManagedProjectListResult(
        items=[
            ManagedProjectSummaryRow(
                id=7,
                name="Apollo",
                status=ProjectStatus.ACTIVE,
                end_date=date(2026, 12, 31),
                health_status=HealthStatus.ON_TRACK,
                computed_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            )
        ]
    )
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, service)
    client = TestClient(app)

    response = client.get("/projects/mine")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["name"] == "Apollo"
    assert body["items"][0]["health_status"] == HealthStatus.ON_TRACK
    service.list_by_manager.assert_awaited_once_with(manager)


def test_get_manager_project_detail(app: FastAPI):
    service = AsyncMock()
    service.get_manager_project_detail.return_value = ManagerProjectDetailResult(
        id=7,
        name="Apollo",
        end_date=date(2026, 12, 31),
        status=ProjectStatus.ACTIVE,
        health_status=HealthStatus.AT_RISK,
        computed_at=None,
        risk_flags=[
            RiskFlagView(flag_text="Overdue milestone", is_positive=False, sort_order=1)
        ],
        milestones=[
            ManagerMilestoneRow(
                id=1,
                title="MVP",
                due_date=date(2026, 8, 1),
                story_points=5,
                status=MilestoneStatus.IN_PROGRESS,
                sort_order=1,
                is_overdue=False,
            )
        ],
        allocations=[
            ManagerAllocationRow(
                resource_name="Ada",
                utilisation_percent=50,
                from_date=date(2026, 1, 1),
                to_date=date(2026, 6, 30),
            )
        ],
    )
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, service)
    client = TestClient(app)

    response = client.get("/projects/mine/7")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Apollo"
    assert body["allocations"][0]["resource_name"] == "Ada"
    service.get_manager_project_detail.assert_awaited_once_with(manager, 7)


def test_get_project(app: FastAPI):
    service = AsyncMock()
    service.get_project.return_value = _project()
    _bind(app, _user(UserRole.ADMIN), service)
    client = TestClient(app)

    response = client.get("/projects/7")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Apollo"
    assert body["manager_name"] == "Mgr One"
    service.get_project.assert_awaited_once_with(7)


def test_update_project(app: FastAPI):
    service = AsyncMock()
    service.update_project.return_value = _project()
    _bind(app, _user(UserRole.ADMIN), service)
    client = TestClient(app)

    response = client.put(
        "/projects/7",
        json={
            "name": "Apollo",
            "description": "Updated",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": ProjectStatus.ACTIVE,
            "manager_id": 4,
            "total_story_points": 25,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 7
    assert body["message"] == ProjectMessage.PROJECT_UPDATED
    service.update_project.assert_awaited_once()
