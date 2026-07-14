from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.core.exceptions import (
    DuplicateEmailError,
    EmployeeAlreadyActiveError,
    EmployeeAlreadyInactiveError,
    EmployeeNotFoundError,
    InvalidManagerRoleError,
    InvalidUserRoleForEmployeeError,
    ManagerProfileNotFoundError,
    ManagerUserNotFoundError,
    ResourceStatusNotFoundError,
    SelfManagerAssignmentError,
    UserNotFoundError,
)
from server.models.enums import ResourceStatusEnum, UserRole
from server.schemas.requests.resource import AssignManagerRequest, UpdateEmployeeRequest
from server.services.resource_service import EmployeeService


@pytest.fixture
def resource_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def allocation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def department_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def designation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def resource_status_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    resource_repo,
    user_repo,
    allocation_repo,
    department_repo,
    designation_repo,
    resource_status_repo,
) -> EmployeeService:
    return EmployeeService(
        resource_repo,
        user_repo,
        allocation_repo,
        department_repo,
        designation_repo,
        resource_status_repo,
    )


def _user(
    *,
    user_id: int = 1,
    role: UserRole = UserRole.RESOURCE,
    email: str = "ada@example.com",
) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.full_name = "Ada"
    user.role = SimpleNamespace(name=role.value)
    return user


def _update_dto(**overrides) -> UpdateEmployeeRequest:
    base = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "department": "Engineering",
        "designation": "Engineer",
    }
    base.update(overrides)
    return UpdateEmployeeRequest(**base)


@pytest.mark.asyncio
async def test_update_raises_when_user_missing(service, user_repo):
    user_repo.find_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        await service.update_resource(1, _update_dto())


@pytest.mark.asyncio
async def test_update_rejects_admin_role(service, user_repo):
    user_repo.find_by_id.return_value = _user(role=UserRole.ADMIN)
    with pytest.raises(InvalidUserRoleForEmployeeError):
        await service.update_resource(1, _update_dto())


@pytest.mark.asyncio
async def test_update_rejects_duplicate_email(service, user_repo):
    user_repo.find_by_id.return_value = _user(user_id=1)
    other = _user(user_id=2, email="taken@example.com")
    user_repo.find_by_email.return_value = other
    with pytest.raises(DuplicateEmailError):
        await service.update_resource(1, _update_dto(email="taken@example.com"))


@pytest.mark.asyncio
async def test_update_creates_resource_when_missing(
    service,
    user_repo,
    resource_repo,
    department_repo,
    designation_repo,
    resource_status_repo,
):
    user = _user()
    user_repo.find_by_id.return_value = user
    user_repo.find_by_email.return_value = user
    department_repo.find_or_create_by_name.return_value = SimpleNamespace(id=3)
    designation_repo.find_or_create_by_name.return_value = SimpleNamespace(id=4)
    resource_repo.find_by_user_id.return_value = None
    resource_status_repo.find_by_name.return_value = SimpleNamespace(id=5)
    saved = SimpleNamespace(id=10)
    resource_repo.save.return_value = saved
    loaded = SimpleNamespace(id=10, user=user)
    resource_repo.get_by_id_with_user.return_value = loaded

    result = await service.update_resource(1, _update_dto())

    assert result.created is True
    assert result.resource is loaded
    resource_status_repo.find_by_name.assert_awaited_once_with(
        ResourceStatusEnum.BENCH.value
    )


@pytest.mark.asyncio
async def test_update_creates_raises_when_bench_status_missing(
    service,
    user_repo,
    resource_repo,
    department_repo,
    designation_repo,
    resource_status_repo,
):
    user = _user()
    user_repo.find_by_id.return_value = user
    user_repo.find_by_email.return_value = None
    department_repo.find_or_create_by_name.return_value = SimpleNamespace(id=3)
    designation_repo.find_or_create_by_name.return_value = SimpleNamespace(id=4)
    resource_repo.find_by_user_id.return_value = None
    resource_status_repo.find_by_name.return_value = None

    with pytest.raises(ResourceStatusNotFoundError):
        await service.update_resource(1, _update_dto())


@pytest.mark.asyncio
async def test_update_existing_resource(
    service,
    user_repo,
    resource_repo,
    department_repo,
    designation_repo,
):
    user = _user()
    user_repo.find_by_id.return_value = user
    user_repo.find_by_email.return_value = None
    department_repo.find_or_create_by_name.return_value = SimpleNamespace(id=3)
    designation_repo.find_or_create_by_name.return_value = SimpleNamespace(id=4)
    existing = SimpleNamespace(id=10, department_id=1, designation_id=2)
    resource_repo.find_by_user_id.return_value = existing
    resource_repo.save.return_value = existing
    resource_repo.get_by_id_with_user.return_value = existing

    result = await service.update_resource(1, _update_dto())

    assert result.created is False
    assert existing.department_id == 3
    assert existing.designation_id == 4


@pytest.mark.asyncio
async def test_list_resources(service, resource_repo):
    resource_repo.list_resources.return_value = [SimpleNamespace(id=1)]
    resource_repo.count_active_resources.return_value = 1
    resource_repo.count_by_status.side_effect = [2, 3]

    result = await service.list_resources(
        status=ResourceStatusEnum.BENCH,
        department="Engineering",
        limit=10,
        offset=0,
    )

    assert result.total == 1
    assert result.bench_count == 2
    assert result.allocated_count == 3
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_get_resource_not_found(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = None
    with pytest.raises(EmployeeNotFoundError):
        await service.get_resource(99)


@pytest.mark.asyncio
async def test_get_resource_by_user_id(service, resource_repo):
    resource = SimpleNamespace(id=10)
    resource_repo.find_by_user_id.return_value = resource
    loaded = SimpleNamespace(id=10, user=MagicMock())
    resource_repo.get_by_id_with_user.return_value = loaded

    result = await service.get_resource_by_user_id(1)

    assert result is loaded


@pytest.mark.asyncio
async def test_get_resource_by_user_id_missing(service, resource_repo):
    resource_repo.find_by_user_id.return_value = None
    with pytest.raises(EmployeeNotFoundError):
        await service.get_resource_by_user_id(1)


@pytest.mark.asyncio
async def test_get_active_allocations(service, resource_repo, allocation_repo):
    resource_repo.get_by_id_with_user.return_value = SimpleNamespace(id=10)
    allocation_repo.find_active_by_resource.return_value = ["a"]

    result = await service.get_active_allocations(10)

    assert result == ["a"]


@pytest.mark.asyncio
async def test_assign_manager_rejects_self_user_ids(service):
    dto = AssignManagerRequest(resource_user_id=1, manager_user_id=1)
    with pytest.raises(SelfManagerAssignmentError):
        await service.assign_manager(dto)


@pytest.mark.asyncio
async def test_assign_manager_resource_missing(service, resource_repo):
    resource_repo.find_by_user_id.return_value = None
    with pytest.raises(EmployeeNotFoundError):
        await service.assign_manager(
            AssignManagerRequest(resource_user_id=1, manager_user_id=2)
        )


@pytest.mark.asyncio
async def test_assign_manager_user_missing(service, resource_repo, user_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    user_repo.find_by_id.return_value = None
    with pytest.raises(ManagerUserNotFoundError):
        await service.assign_manager(
            AssignManagerRequest(resource_user_id=1, manager_user_id=2)
        )


@pytest.mark.asyncio
async def test_assign_manager_wrong_role(service, resource_repo, user_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    user_repo.find_by_id.return_value = _user(user_id=2, role=UserRole.RESOURCE)
    with pytest.raises(InvalidManagerRoleError):
        await service.assign_manager(
            AssignManagerRequest(resource_user_id=1, manager_user_id=2)
        )


@pytest.mark.asyncio
async def test_assign_manager_profile_missing(service, resource_repo, user_repo):
    resource_repo.find_by_user_id.side_effect = [
        SimpleNamespace(id=10),
        None,
    ]
    user_repo.find_by_id.return_value = _user(user_id=2, role=UserRole.MANAGER)
    with pytest.raises(ManagerProfileNotFoundError):
        await service.assign_manager(
            AssignManagerRequest(resource_user_id=1, manager_user_id=2)
        )


@pytest.mark.asyncio
async def test_assign_manager_same_resource_ids(service, resource_repo, user_repo):
    same = SimpleNamespace(id=10, manager_id=None)
    resource_repo.find_by_user_id.side_effect = [same, same]
    user_repo.find_by_id.return_value = _user(user_id=2, role=UserRole.MANAGER)
    with pytest.raises(SelfManagerAssignmentError):
        await service.assign_manager(
            AssignManagerRequest(resource_user_id=1, manager_user_id=2)
        )


@pytest.mark.asyncio
async def test_assign_manager_happy_path(service, resource_repo, user_repo):
    resource = SimpleNamespace(id=10, manager_id=None)
    manager = SimpleNamespace(id=20)
    resource_repo.find_by_user_id.side_effect = [resource, manager]
    user_repo.find_by_id.return_value = _user(user_id=2, role=UserRole.MANAGER)
    resource_repo.save.return_value = resource

    result = await service.assign_manager(
        AssignManagerRequest(resource_user_id=1, manager_user_id=2)
    )

    assert result.manager_id == 20
    resource_repo.save.assert_awaited_once_with(resource)


@pytest.mark.asyncio
async def test_deactivate_already_inactive(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = SimpleNamespace(
        id=10, is_active=False
    )
    with pytest.raises(EmployeeAlreadyInactiveError):
        await service.deactivate_resource(10)


@pytest.mark.asyncio
async def test_deactivate_ends_allocations(
    service, resource_repo, allocation_repo, resource_status_repo
):
    resource = SimpleNamespace(id=10, is_active=True, resource_status_id=1)
    resource_repo.get_by_id_with_user.return_value = resource
    allocation = SimpleNamespace(to_date=None)
    allocation_repo.find_active_by_resource.return_value = [allocation]
    resource_status_repo.find_by_name.return_value = SimpleNamespace(id=9)

    result = await service.deactivate_resource(10)

    assert result.is_active is False
    assert result.resource_status_id == 9
    allocation_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_raises_when_bench_missing(
    service, resource_repo, allocation_repo, resource_status_repo
):
    resource_repo.get_by_id_with_user.return_value = SimpleNamespace(
        id=10, is_active=True
    )
    allocation_repo.find_active_by_resource.return_value = []
    resource_status_repo.find_by_name.return_value = None
    with pytest.raises(ResourceStatusNotFoundError):
        await service.deactivate_resource(10)


@pytest.mark.asyncio
async def test_reactivate_already_active(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = SimpleNamespace(
        id=10, is_active=True
    )
    with pytest.raises(EmployeeAlreadyActiveError):
        await service.reactivate_resource(10)


@pytest.mark.asyncio
async def test_reactivate_happy_path(
    service, resource_repo, resource_status_repo
):
    resource = SimpleNamespace(id=10, is_active=False, resource_status_id=1)
    resource_repo.get_by_id_with_user.side_effect = [resource, resource]
    resource_status_repo.find_by_name.return_value = SimpleNamespace(id=9)
    resource_repo.save.return_value = resource

    result = await service.reactivate_resource(10)

    assert result.is_active is True
    assert result.resource_status_id == 9
