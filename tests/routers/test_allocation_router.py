from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import UserRole
from server.routers.allocation_router import AllocationRouter
from server.schemas.response_values import AllocationMessage
from server.schemas.responses.allocation import (
    BulkAllocationCreatedItemResponse,
    BulkAllocationCreatedResponse,
    MyAllocationListResponse,
    MyAllocationSummaryResponse,
    WeekAllocationContextResponse,
    WeekProjectAllocationResponse,
)
from server.services.allocation_view_service import AllocationListResult


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(AllocationRouter().router)
    return application


def _user(role: UserRole):
    user = MagicMock()
    user.id = 1
    user.force_password_change = False
    user.role = SimpleNamespace(name=role.value)
    return user


def _bind(app: FastAPI, user, dep, service):
    async def override_user():
        return user

    async def override_service():
        return service

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    app.dependency_overrides[dep] = override_service


def _allocation_row():
    resource = MagicMock()
    resource.user = SimpleNamespace(full_name="Ada Lovelace")
    project = SimpleNamespace(name="Apollo")
    return SimpleNamespace(
        id=11,
        resource_id=2,
        resource=resource,
        project=project,
        utilisation_percent=50,
        from_date=date(2026, 1, 1),
        to_date=date(2026, 3, 31),
    )


def test_list_allocations(app: FastAPI):
    view_service = AsyncMock()
    view_service.list_allocations.return_value = AllocationListResult(
        items=[_allocation_row()], total=1
    )
    _bind(
        app,
        _user(UserRole.ADMIN),
        dependency_provider.get_allocation_view_service,
        view_service,
    )
    client = TestClient(app)

    response = client.get("/allocations?limit=10&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["resource_name"] == "Ada Lovelace"
    assert body["items"][0]["project_name"] == "Apollo"
    view_service.list_allocations.assert_awaited_once()


def test_create_allocation(app: FastAPI):
    service = AsyncMock()
    service.create_allocation.return_value = _allocation_row()
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, dependency_provider.get_allocation_service, service)
    client = TestClient(app)

    response = client.post(
        "/allocations",
        json={
            "resource_id": 2,
            "project_id": 3,
            "utilisation_percent": 50,
            "from_date": "2026-01-01",
            "to_date": "2026-03-31",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == AllocationMessage.ALLOCATION_CREATED
    assert body["resource_name"] == "Ada Lovelace"
    service.create_allocation.assert_awaited_once()
    assert service.create_allocation.await_args.args[1] is manager


def test_bulk_create_allocations(app: FastAPI):
    service = AsyncMock()
    service.bulk_create.return_value = BulkAllocationCreatedResponse(
        project_id=3,
        project_name="Apollo",
        message=AllocationMessage.ALLOCATION_CREATED,
        items=[
            BulkAllocationCreatedItemResponse(
                id=11,
                resource_id=2,
                resource_name="Ada Lovelace",
                role_key="role_1",
                utilisation_percent=50,
                from_date=date(2026, 1, 1),
                to_date=date(2026, 3, 31),
            )
        ],
    )
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, dependency_provider.get_allocation_service, service)
    client = TestClient(app)

    response = client.post(
        "/allocations/bulk",
        json={
            "project_id": 3,
            "utilisation_percent": 50,
            "from_date": "2026-01-01",
            "to_date": "2026-03-31",
            "items": [{"resource_id": 2, "role_key": "role_1"}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project_name"] == "Apollo"
    assert len(body["items"]) == 1
    service.bulk_create.assert_awaited_once()


def test_list_my_allocations(app: FastAPI):
    service = AsyncMock()
    service.list_my_allocations.return_value = MyAllocationListResponse(
        items=[
            MyAllocationSummaryResponse(
                project_name="Apollo",
                utilisation_percent=40,
                from_date=date(2026, 1, 1),
                to_date=date(2026, 3, 31),
                status="ACTIVE",
            )
        ],
        total_utilisation_percent=40,
    )
    resource = _user(UserRole.RESOURCE)
    _bind(app, resource, dependency_provider.get_allocation_service, service)
    client = TestClient(app)

    response = client.get("/allocations/mine")

    assert response.status_code == 200
    body = response.json()
    assert body["total_utilisation_percent"] == 40
    service.list_my_allocations.assert_awaited_once_with(resource, week_start=None)


def test_list_my_allocations_week_context(app: FastAPI):
    service = AsyncMock()
    service.list_my_allocations.return_value = WeekAllocationContextResponse(
        week_start=date(2026, 7, 13),
        max_weekly_hours=40,
        projects=[
            WeekProjectAllocationResponse(
                project_id=3,
                project_name="Apollo",
                utilisation_percent=50,
                max_hours=20.0,
            )
        ],
    )
    resource = _user(UserRole.RESOURCE)
    _bind(app, resource, dependency_provider.get_allocation_service, service)
    client = TestClient(app)

    response = client.get("/allocations/mine?week_start=2026-07-13")

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == "2026-07-13"
    assert body["projects"][0]["project_name"] == "Apollo"


def test_list_project_allocations(app: FastAPI):
    service = AsyncMock()
    project = SimpleNamespace(name="Apollo")
    service.list_project_allocations.return_value = (project, [_allocation_row()])
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, dependency_provider.get_allocation_service, service)
    client = TestClient(app)

    response = client.get("/allocations/by-project/3")

    assert response.status_code == 200
    body = response.json()
    assert body["project_name"] == "Apollo"
    assert body["items"][0]["resource_name"] == "Ada Lovelace"
    service.list_project_allocations.assert_awaited_once_with(3, manager)


def test_end_allocation(app: FastAPI):
    service = AsyncMock()
    service.end_allocation.return_value = _allocation_row()
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, dependency_provider.get_allocation_service, service)
    client = TestClient(app)

    response = client.post("/allocations/11/end")

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == AllocationMessage.ALLOCATION_ENDED
    assert body["end_date"] == "2026-03-31"
    service.end_allocation.assert_awaited_once_with(11, manager)
