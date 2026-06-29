from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.core.exceptions import (
    AllocationNotFoundError,
    EmployeeNotAllocatableError,
    EmployeeNotFoundError,
    InvalidAllocationDatesError,
    InvalidProjectStatusForAllocationError,
    ManagerProfileNotFoundError,
    NotProjectOwnerError,
    OverAllocationError,
    ProjectNotFoundError,
    ResourceStatusNotFoundError,
)
from server.models.enums import ProjectStatus, ResourceStatusEnum
from server.schemas.requests.allocation import (
    BulkAllocationItemRequest,
    BulkCreateAllocationRequest,
    CreateAllocationRequest,
)
from server.services.allocation_service import AllocationService

@pytest.fixture
def resource_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def allocation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def system_config_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def resource_status_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    resource_repo,
    project_repo,
    allocation_repo,
    system_config_repo,
    resource_status_repo,
) -> AllocationService:
    return AllocationService(
        resource_repo,
        project_repo,
        allocation_repo,
        system_config_repo,
        resource_status_repo,
        allocation_notification_service=None,
    )


def _user(user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(id=user_id)


def _manager_resource(manager_id: int = 100) -> SimpleNamespace:
    return SimpleNamespace(id=manager_id)


def _team_resource(*, resource_id: int = 10, manager_id: int = 100) -> SimpleNamespace:
    return SimpleNamespace(
        id=resource_id,
        is_active=True,
        manager_id=manager_id,
        resource_status_id=None,
    )


def _project(*, project_id: int = 5, manager_id: int = 100, status=ProjectStatus.ACTIVE):
    return SimpleNamespace(id=project_id, manager_id=manager_id, status=status, name="P1")


def _create_dto(**overrides) -> CreateAllocationRequest:
    base = {
        "resource_id": 10,
        "project_id": 5,
        "utilisation_percent": 50,
        "from_date": date(2026, 1, 1),
        "to_date": date(2026, 3, 1),
    }
    base.update(overrides)
    return CreateAllocationRequest(**base)


@pytest.mark.asyncio
async def test_validate_utilisation_allows_under_100(service, allocation_repo):
    allocation_repo.find_overlapping.return_value = [
        SimpleNamespace(utilisation_percent=40),
        SimpleNamespace(utilisation_percent=30),
    ]
    await service.validate_utilisation(10, date(2026, 1, 1), date(2026, 2, 1), 30)


@pytest.mark.asyncio
async def test_validate_utilisation_rejects_over_allocation(service, allocation_repo):
    allocation_repo.find_overlapping.return_value = [
        SimpleNamespace(utilisation_percent=80),
    ]
    with pytest.raises(OverAllocationError, match="110%"):
        await service.validate_utilisation(10, date(2026, 1, 1), date(2026, 2, 1), 30)


@pytest.mark.asyncio
async def test_create_requires_manager_profile(service, resource_repo):
    resource_repo.find_by_user_id.return_value = None
    with pytest.raises(ManagerProfileNotFoundError):
        await service.create_allocation(_create_dto(), _user())


@pytest.mark.asyncio
async def test_create_rejects_missing_resource(service, resource_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = None
    with pytest.raises(EmployeeNotFoundError):
        await service.create_allocation(_create_dto(), _user())


@pytest.mark.asyncio
async def test_create_rejects_resource_not_on_team(service, resource_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = _team_resource(manager_id=999)
    with pytest.raises(EmployeeNotAllocatableError):
        await service.create_allocation(_create_dto(), _user())


@pytest.mark.asyncio
async def test_create_rejects_missing_project(service, resource_repo, project_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = _team_resource()
    project_repo.get_by_id_with_manager.return_value = None
    with pytest.raises(ProjectNotFoundError):
        await service.create_allocation(_create_dto(), _user())


@pytest.mark.asyncio
async def test_create_rejects_on_hold_project(service, resource_repo, project_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = _team_resource()
    project_repo.get_by_id_with_manager.return_value = _project(
        status=ProjectStatus.ON_HOLD
    )
    with pytest.raises(InvalidProjectStatusForAllocationError):
        await service.create_allocation(_create_dto(), _user())


@pytest.mark.asyncio
async def test_create_rejects_invalid_dates(service, resource_repo, project_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = _team_resource()
    project_repo.get_by_id_with_manager.return_value = _project()
    with pytest.raises(InvalidAllocationDatesError):
        await service.create_allocation(
            _create_dto(from_date=date(2026, 3, 1), to_date=date(2026, 3, 1)),
            _user(),
        )


@pytest.mark.asyncio
async def test_create_allocation_happy_path(
    service,
    resource_repo,
    project_repo,
    allocation_repo,
    resource_status_repo,
):
    resource = _team_resource()
    project = _project()
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = resource
    project_repo.get_by_id_with_manager.return_value = project
    allocation_repo.find_overlapping.return_value = []
    saved = SimpleNamespace(id=1, resource_id=10, project_id=5)
    allocation_repo.save.return_value = saved
    resource_status_repo.find_by_name.return_value = SimpleNamespace(
        id=2, name=ResourceStatusEnum.ALLOCATED.value
    )
    resource_repo.save.return_value = resource

    result = await service.create_allocation(_create_dto(), _user())

    assert result.id == 1
    assert result.resource is resource
    assert result.project is project
    resource_status_repo.find_by_name.assert_awaited_once_with(
        ResourceStatusEnum.ALLOCATED.value
    )


@pytest.mark.asyncio
async def test_create_raises_when_status_missing(
    service,
    resource_repo,
    project_repo,
    allocation_repo,
    resource_status_repo,
):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = _team_resource()
    project_repo.get_by_id_with_manager.return_value = _project()
    allocation_repo.find_overlapping.return_value = []
    allocation_repo.save.return_value = SimpleNamespace(id=1)
    resource_status_repo.find_by_name.return_value = None

    with pytest.raises(ResourceStatusNotFoundError):
        await service.create_allocation(_create_dto(), _user())


@pytest.mark.asyncio
async def test_end_allocation_requires_owner(
    service, resource_repo, allocation_repo
):
    resource_repo.find_by_user_id.return_value = _manager_resource(manager_id=100)
    allocation_repo.get_by_id_with_relations.return_value = SimpleNamespace(
        id=1,
        project=SimpleNamespace(manager_id=999),
        resource_id=10,
    )
    with pytest.raises(NotProjectOwnerError):
        await service.end_allocation(1, _user())


@pytest.mark.asyncio
async def test_end_allocation_not_found(service, resource_repo, allocation_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    allocation_repo.get_by_id_with_relations.return_value = None
    with pytest.raises(AllocationNotFoundError):
        await service.end_allocation(1, _user())


@pytest.mark.asyncio
async def test_list_project_allocations_owner_only(
    service, resource_repo, project_repo, allocation_repo
):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    project_repo.get_by_id_with_manager.return_value = _project(manager_id=100)
    allocation_repo.find_active_by_project.return_value = []
    project, items = await service.list_project_allocations(5, _user())
    assert project.id == 5
    assert items == []

    project_repo.get_by_id_with_manager.return_value = _project(manager_id=999)
    with pytest.raises(NotProjectOwnerError):
        await service.list_project_allocations(5, _user())


@pytest.mark.asyncio
async def test_bulk_create_happy_path(
    service,
    resource_repo,
    project_repo,
    allocation_repo,
    resource_status_repo,
):
    resource = _team_resource()
    project = _project()
    resource_repo.find_by_user_id.return_value = _manager_resource()
    resource_repo.get_by_id_with_user.return_value = resource
    project_repo.get_by_id_with_manager.return_value = project
    allocation_repo.find_overlapping.return_value = []
    saved = SimpleNamespace(
        id=9,
        resource_id=10,
        utilisation_percent=40,
        from_date=date(2026, 1, 1),
        to_date=date(2026, 3, 1),
    )
    allocation_repo.save.return_value = saved
    resource_status_repo.find_by_name.return_value = SimpleNamespace(
        id=2, name=ResourceStatusEnum.ALLOCATED.value
    )
    resource.user = SimpleNamespace(full_name="Ada Lovelace")

    dto = BulkCreateAllocationRequest(
        project_id=5,
        utilisation_percent=40,
        from_date=date(2026, 1, 1),
        to_date=date(2026, 3, 1),
        items=[BulkAllocationItemRequest(resource_id=10, role_key="backend")],
    )
    result = await service.bulk_create(dto, _user())

    assert result.project_id == 5
    assert len(result.items) == 1
    assert result.items[0].role_key == "backend"
    assert result.items[0].resource_name == "Ada Lovelace"


@pytest.mark.asyncio
async def test_bulk_create_project_not_found(service, resource_repo, project_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    project_repo.get_by_id_with_manager.return_value = None
    dto = BulkCreateAllocationRequest(
        project_id=5,
        utilisation_percent=40,
        from_date=date(2026, 1, 1),
        to_date=date(2026, 3, 1),
        items=[BulkAllocationItemRequest(resource_id=10)],
    )
    with pytest.raises(ProjectNotFoundError):
        await service.bulk_create(dto, _user())


@pytest.mark.asyncio
async def test_bulk_create_not_owner(service, resource_repo, project_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    project_repo.get_by_id_with_manager.return_value = _project(manager_id=999)
    dto = BulkCreateAllocationRequest(
        project_id=5,
        utilisation_percent=40,
        from_date=date(2026, 1, 1),
        to_date=date(2026, 3, 1),
        items=[BulkAllocationItemRequest(resource_id=10)],
    )
    with pytest.raises(NotProjectOwnerError):
        await service.bulk_create(dto, _user())


@pytest.mark.asyncio
async def test_list_managed_projects(service, resource_repo, project_repo):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    project_repo.find_by_manager_id.return_value = [_project()]
    result = await service.list_managed_projects(_user())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_my_allocations(service, resource_repo, allocation_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    allocation_repo.find_active_by_resource.return_value = [
        SimpleNamespace(
            project=SimpleNamespace(name="Apollo"),
            utilisation_percent=50,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 6, 1),
        )
    ]
    result = await service.list_my_allocations(_user())
    assert result.total_utilisation_percent == 50
    assert result.items[0].project_name == "Apollo"


@pytest.mark.asyncio
async def test_recompute_all_resource_statuses(
    service, resource_repo, allocation_repo, resource_status_repo
):
    resources = [
        SimpleNamespace(id=1, resource_status_id=None),
        SimpleNamespace(id=2, resource_status_id=None),
    ]
    resource_repo.list_active.return_value = resources
    allocation_repo.find_all_active.return_value = [
        SimpleNamespace(resource_id=1),
    ]
    resource_status_repo.find_by_name.side_effect = lambda name: SimpleNamespace(
        id=1 if name == ResourceStatusEnum.ALLOCATED.value else 2
    )

    result = await service.recompute_all_resource_statuses()

    assert result.allocated_count == 1
    assert result.bench_count == 1


@pytest.mark.asyncio
async def test_end_allocation_happy_path(
    service, resource_repo, allocation_repo, resource_status_repo
):
    resource_repo.find_by_user_id.return_value = _manager_resource()
    allocation = SimpleNamespace(
        id=1,
        resource_id=10,
        project=SimpleNamespace(manager_id=100),
        to_date=date(2026, 12, 1),
    )
    reloaded = SimpleNamespace(id=1, resource_id=10)
    allocation_repo.get_by_id_with_relations.side_effect = [allocation, reloaded]
    allocation_repo.save.return_value = allocation
    resource_repo.get_by_id_with_user.return_value = _team_resource()
    allocation_repo.find_active_by_resource.return_value = [allocation]
    resource_status_repo.find_by_name.return_value = SimpleNamespace(id=2)

    result = await service.end_allocation(1, _user())

    assert result is reloaded
    allocation_repo.save.assert_awaited()
