from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.core.exceptions import (
    EmployeeNotFoundError,
    InvalidManagerRoleError,
    InvalidProjectDatesError,
    InvalidProjectManagerError,
    InvalidProjectStatusError,
    InvalidStoryPointsError,
    ManagerProfileNotFoundError,
    ProjectNotFoundError,
)
from server.models.enums import ProjectStatus, UserRole
from server.schemas.requests.project import CreateProjectRequest, UpdateProjectRequest
from server.services.project_service import ProjectService


@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def resource_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def milestone_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def allocation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def health_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    project_repo, resource_repo, milestone_repo, allocation_repo, health_service
) -> ProjectService:
    return ProjectService(
        project_repo,
        resource_repo,
        milestone_repo,
        allocation_repo,
        health_service,
    )


def _create_dto(**overrides) -> CreateProjectRequest:
    base = {
        "name": "Alpha",
        "description": "desc",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 6, 1),
        "status": ProjectStatus.PLANNED,
        "manager_id": 7,
        "total_story_points": 20,
    }
    base.update(overrides)
    return CreateProjectRequest(**base)


def _manager_resource(*, active: bool = True, role: str = UserRole.MANAGER) -> SimpleNamespace:
    return SimpleNamespace(
        id=7,
        is_active=active,
        user=SimpleNamespace(role=SimpleNamespace(name=role)),
    )


@pytest.mark.asyncio
async def test_create_rejects_invalid_dates(service):
    with pytest.raises(InvalidProjectDatesError):
        await service.create_project(
            _create_dto(start_date=date(2026, 6, 1), end_date=date(2026, 6, 1))
        )


@pytest.mark.asyncio
async def test_create_rejects_negative_story_points(service):
    # pydantic Field(ge=0) blocks negatives on DTO; call validator directly
    with pytest.raises(InvalidStoryPointsError):
        service._validate_story_points(-1)


@pytest.mark.asyncio
async def test_create_rejects_completed_status(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = _manager_resource()
    with pytest.raises(InvalidProjectStatusError):
        await service.create_project(_create_dto(status=ProjectStatus.COMPLETED))


@pytest.mark.asyncio
async def test_create_rejects_missing_manager(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = None
    with pytest.raises(EmployeeNotFoundError):
        await service.create_project(_create_dto())


@pytest.mark.asyncio
async def test_create_rejects_inactive_manager(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = _manager_resource(active=False)
    with pytest.raises(InvalidProjectManagerError):
        await service.create_project(_create_dto())


@pytest.mark.asyncio
async def test_create_rejects_non_manager_role(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = _manager_resource(
        role=UserRole.RESOURCE
    )
    with pytest.raises(InvalidManagerRoleError):
        await service.create_project(_create_dto())


@pytest.mark.asyncio
async def test_create_project_happy_path(service, resource_repo, project_repo):
    resource_repo.get_by_id_with_user.return_value = _manager_resource()
    saved = SimpleNamespace(id=1, name="Alpha")
    project_repo.save.return_value = saved

    result = await service.create_project(_create_dto())

    assert result is saved
    project_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_project_not_found(service, project_repo):
    project_repo.get_by_id_with_manager.return_value = None
    with pytest.raises(ProjectNotFoundError):
        await service.get_project(1)


@pytest.mark.asyncio
async def test_update_project_not_found(service, project_repo):
    project_repo.get_by_id_with_manager.return_value = None
    dto = UpdateProjectRequest(**_create_dto().model_dump())
    with pytest.raises(ProjectNotFoundError):
        await service.update_project(1, dto)


@pytest.mark.asyncio
async def test_list_projects(service, project_repo):
    project_repo.list_projects.return_value = [SimpleNamespace(id=1)]
    project_repo.count_projects.return_value = 1
    result = await service.list_projects(status=None, limit=10, offset=0)
    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_list_by_manager_requires_profile(service, resource_repo):
    resource_repo.find_by_user_id.return_value = None
    with pytest.raises(ManagerProfileNotFoundError):
        await service.list_by_manager(SimpleNamespace(id=1))


@pytest.mark.asyncio
async def test_to_milestone_row_marks_overdue():
    today = date(2026, 7, 1)
    overdue = SimpleNamespace(
        id=1,
        title="M1",
        due_date=date(2026, 6, 1),
        story_points=5,
        status="IN_PROGRESS",
        sort_order=1,
    )
    done = SimpleNamespace(
        id=2,
        title="M2",
        due_date=date(2026, 6, 1),
        story_points=3,
        status="DONE",
        sort_order=2,
    )
    assert ProjectService._to_milestone_row(overdue, today).is_overdue is True
    assert ProjectService._to_milestone_row(done, today).is_overdue is False
