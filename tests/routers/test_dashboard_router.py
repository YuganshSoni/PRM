from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import ResourceStatusEnum, UserRole
from server.routers.dashboard_router import DashboardRouter
from server.schemas.responses.dashboard import (
    ActiveEmployeeSummary,
    BenchEmployeeSummary,
    DashboardAllocationSummary,
    DashboardEmployeeDetailResponse,
    DashboardStatsResponse,
    ResourceDashboardResponse,
)


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(DashboardRouter().router)
    return application


def _manager():
    user = MagicMock()
    user.id = 10
    user.force_password_change = False
    user.role = SimpleNamespace(name=UserRole.MANAGER.value)
    return user


def _override(app: FastAPI, service):
    manager = _manager()

    async def override_user():
        return manager

    async def override_service():
        return service

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    app.dependency_overrides[dependency_provider.get_resource_dashboard_service] = (
        override_service
    )
    return manager


def test_get_resource_dashboard(app: FastAPI):
    service = AsyncMock()
    service.get_resource_dashboard.return_value = ResourceDashboardResponse(
        bench_resources=[
            BenchEmployeeSummary(
                id=1, full_name="Ada", department="Eng", skills=["Python"]
            )
        ],
        active_resources=[
            ActiveEmployeeSummary(
                id=2,
                full_name="Bob",
                utilisation_percent=50,
                availability_label="Partial",
            )
        ],
        stats=DashboardStatsResponse(bench_count=1, partial_count=1),
        month_label="July 2026",
    )
    manager = _override(app, service)
    client = TestClient(app)

    response = client.get("/dashboard/resources")

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["bench_count"] == 1
    assert body["bench_resources"][0]["full_name"] == "Ada"
    service.get_resource_dashboard.assert_awaited_once_with(manager)


def test_get_resource_detail(app: FastAPI):
    service = AsyncMock()
    service.get_resource_detail.return_value = DashboardEmployeeDetailResponse(
        id=2,
        full_name="Bob",
        department="Eng",
        status=ResourceStatusEnum.ALLOCATED,
        utilisation_percent=75,
        skills=["Go"],
        active_allocations=[
            DashboardAllocationSummary(
                project_name="Apollo",
                utilisation_percent=75,
                from_date=date(2026, 1, 1),
                to_date=date(2026, 6, 30),
            )
        ],
        recent_activity_tags=["Development"],
    )
    manager = _override(app, service)
    client = TestClient(app)

    response = client.get("/dashboard/resources/2")

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Bob"
    assert body["status"] == ResourceStatusEnum.ALLOCATED
    service.get_resource_detail.assert_awaited_once_with(2, manager)
