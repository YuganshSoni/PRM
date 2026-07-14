from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import (
    ProficiencyLevel,
    ResourceStatusEnum,
    SkillCategoryEnum,
    UserRole,
    UserStatus,
)
from server.routers.resource_router import EmployeeRouter
from server.schemas.response_values import EmployeeMessage
from server.services.resource_service import EmployeeListResult, EmployeeUpsertResult


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(EmployeeRouter().router)
    return application


def _admin():
    user = MagicMock()
    user.id = 1
    user.force_password_change = False
    user.role = SimpleNamespace(name=UserRole.ADMIN.value)
    return user


def _bind(app: FastAPI, *, resource_service=None, skill_service=None):
    async def override_user():
        return _admin()

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    if resource_service is not None:

        async def override_resource():
            return resource_service

        app.dependency_overrides[dependency_provider.get_resource_service] = (
            override_resource
        )
    if skill_service is not None:

        async def override_skill():
            return skill_service

        app.dependency_overrides[dependency_provider.get_skill_service] = override_skill


def _resource(**overrides):
    user = SimpleNamespace(
        full_name="Ada Lovelace",
        email="ada@example.com",
        status=UserStatus.ACTIVE,
    )
    base = dict(
        id=2,
        user_id=5,
        user=user,
        department=SimpleNamespace(name="Engineering"),
        designation=SimpleNamespace(name="Engineer"),
        resource_status=SimpleNamespace(name=ResourceStatusEnum.BENCH.value),
        is_active=True,
        manager_id=9,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _allocation():
    return SimpleNamespace(
        project=SimpleNamespace(name="Apollo"),
        utilisation_percent=40,
        to_date=date(2026, 6, 30),
    )


def _skill():
    return SimpleNamespace(
        id=3,
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        skill=SimpleNamespace(
            name="Python",
            category=SimpleNamespace(name=SkillCategoryEnum.BACKEND.value),
        ),
    )


def test_list_resources(app: FastAPI):
    service = AsyncMock()
    service.list_resources.return_value = EmployeeListResult(
        items=[_resource()],
        total=1,
        bench_count=1,
        allocated_count=0,
    )
    _bind(app, resource_service=service)
    client = TestClient(app)

    response = client.get("/resources")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Ada Lovelace"
    assert body["bench_count"] == 1


def test_get_resource(app: FastAPI):
    service = AsyncMock()
    service.get_resource.return_value = _resource(
        resource_status=SimpleNamespace(name=ResourceStatusEnum.ALLOCATED.value)
    )
    service.get_active_allocations.return_value = [_allocation()]
    _bind(app, resource_service=service)
    client = TestClient(app)

    response = client.get("/resources/2")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["active_allocations"][0]["project_name"] == "Apollo"
    service.get_resource.assert_awaited_once_with(2)


def test_get_resource_by_user(app: FastAPI):
    service = AsyncMock()
    resource = _resource()
    service.get_resource_by_user_id.return_value = resource
    service.get_active_allocations.return_value = []
    _bind(app, resource_service=service)
    client = TestClient(app)

    response = client.get("/resources/by-user/5")

    assert response.status_code == 200
    assert response.json()["user_id"] == 5
    service.get_resource_by_user_id.assert_awaited_once_with(5)


def test_update_resource(app: FastAPI):
    service = AsyncMock()
    service.update_resource.return_value = EmployeeUpsertResult(
        resource=_resource(), created=False
    )
    _bind(app, resource_service=service)
    client = TestClient(app)

    response = client.put(
        "/resources/by-user/5",
        json={
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "department": "Engineering",
            "designation": "Engineer",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == EmployeeMessage.PROFILE_UPDATED
    assert body["created"] is False


def test_update_resource_created(app: FastAPI):
    service = AsyncMock()
    service.update_resource.return_value = EmployeeUpsertResult(
        resource=_resource(), created=True
    )
    _bind(app, resource_service=service)
    client = TestClient(app)

    response = client.put(
        "/resources/by-user/5",
        json={
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "department": "Engineering",
            "designation": "Engineer",
        },
    )

    assert response.status_code == 201
    assert response.json()["message"] == EmployeeMessage.PROFILE_CREATED


def test_assign_manager(app: FastAPI):
    service = AsyncMock()
    service.assign_manager.return_value = _resource(manager_id=12)
    _bind(app, resource_service=service)
    client = TestClient(app)

    response = client.put(
        "/resources/assign-manager",
        json={"resource_user_id": 5, "manager_user_id": 12},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["manager_id"] == 12
    assert body["message"] == EmployeeMessage.MANAGER_ASSIGNED


def test_deactivate_and_reactivate(app: FastAPI):
    service = AsyncMock()
    service.deactivate_resource.return_value = None
    service.reactivate_resource.return_value = _resource()
    _bind(app, resource_service=service)
    client = TestClient(app)

    deactivate = client.post("/resources/2/deactivate")
    assert deactivate.status_code == 200
    assert deactivate.json()["message"] == EmployeeMessage.EMPLOYEE_DEACTIVATED

    reactivate = client.post("/resources/2/reactivate")
    assert reactivate.status_code == 200
    assert reactivate.json()["message"] == EmployeeMessage.EMPLOYEE_REACTIVATED


def test_list_and_add_skills(app: FastAPI):
    skill_service = AsyncMock()
    skill_service.list_skills.return_value = [_skill()]
    skill_service.add_skill.return_value = _skill()
    _bind(app, skill_service=skill_service)
    client = TestClient(app)

    listed = client.get("/resources/2/skills")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["skill_name"] == "Python"

    added = client.post(
        "/resources/2/skills",
        json={
            "skill_name": "Python",
            "category": SkillCategoryEnum.BACKEND,
            "proficiency_level": ProficiencyLevel.INTERMEDIATE,
        },
    )
    assert added.status_code == 201
    assert added.json()["category"] == SkillCategoryEnum.BACKEND
