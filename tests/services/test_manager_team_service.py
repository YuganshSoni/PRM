from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.core.exceptions import (
    EmployeeNotAllocatableError,
    EmployeeNotFoundError,
    ForbiddenError,
    ManagerProfileNotFoundError,
)
from server.models.enums import ResourceStatusEnum
from server.services.manager_team_service import ManagerTeamService


@pytest.fixture
def resource_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(resource_repo) -> ManagerTeamService:
    return ManagerTeamService(resource_repo)


@pytest.mark.asyncio
async def test_resolve_manager_resource_id_missing(service, resource_repo):
    resource_repo.find_by_user_id.return_value = None
    with pytest.raises(ManagerProfileNotFoundError):
        await service.resolve_manager_resource_id(SimpleNamespace(id=1))


@pytest.mark.asyncio
async def test_resolve_manager_resource_id_happy(service, resource_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=42)
    assert await service.resolve_manager_resource_id(SimpleNamespace(id=1)) == 42


@pytest.mark.asyncio
async def test_list_active_team_members(service, resource_repo):
    resource_repo.find_active_by_manager_id.return_value = [SimpleNamespace(id=1)]
    result = await service.list_active_team_members(100, load_skills=True)
    assert len(result) == 1
    resource_repo.find_active_by_manager_id.assert_awaited_once_with(
        100, load_skills=True
    )


@pytest.mark.asyncio
async def test_list_bench_team_members(service, resource_repo):
    resource_repo.find_by_manager_and_status.return_value = []
    result = await service.list_bench_team_members(100)
    assert result == []
    resource_repo.find_by_manager_and_status.assert_awaited_once_with(
        100, ResourceStatusEnum.BENCH, load_skills=False
    )


@pytest.mark.asyncio
async def test_get_team_member_not_found(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = None
    with pytest.raises(EmployeeNotFoundError):
        await service.get_team_member(100, 10)


@pytest.mark.asyncio
async def test_get_team_member_not_on_team(service, resource_repo):
    resource_repo.get_by_id_with_user.return_value = SimpleNamespace(
        id=10, is_active=True, manager_id=999
    )
    with pytest.raises(EmployeeNotAllocatableError):
        await service.get_team_member(100, 10)


@pytest.mark.asyncio
async def test_get_team_member_happy(service, resource_repo):
    resource = SimpleNamespace(id=10, is_active=True, manager_id=100)
    resource_repo.get_by_id_with_user.return_value = resource
    assert await service.get_team_member(100, 10) is resource


def test_ensure_team_member_rejects_inactive():
    resource = SimpleNamespace(is_active=False, manager_id=100)
    with pytest.raises(EmployeeNotAllocatableError):
        ManagerTeamService.ensure_team_member(100, resource)


def test_ensure_team_member_or_forbidden():
    resource = SimpleNamespace(manager_id=999)
    with pytest.raises(ForbiddenError):
        ManagerTeamService.ensure_team_member_or_forbidden(100, resource)

    ok = SimpleNamespace(manager_id=100)
    ManagerTeamService.ensure_team_member_or_forbidden(100, ok)
