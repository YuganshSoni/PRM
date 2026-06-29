from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.services.resource_dashboard_service import ResourceDashboardService


def _resource(
    *,
    resource_id: int = 1,
    name: str = "Ada Lovelace",
    department: str = "Engineering",
    status: str = "BENCH",
    skills: list | None = None,
):
    resource = MagicMock()
    resource.id = resource_id
    resource.user.full_name = name
    resource.department.name = department
    resource.resource_status.name = status
    resource.skills = skills or []
    return resource


def _skill(name: str = "Python"):
    skill = MagicMock()
    skill.skill.name = name
    return skill


def _allocation(
    *,
    resource_id: int = 1,
    utilisation: int = 50,
    resource=None,
    project_name: str = "Engine",
):
    allocation = MagicMock()
    allocation.resource_id = resource_id
    allocation.utilisation_percent = utilisation
    allocation.resource = resource or _resource(resource_id=resource_id, name="Active")
    allocation.project.name = project_name
    from datetime import date

    allocation.from_date = date(2026, 1, 1)
    allocation.to_date = date(2026, 6, 30)
    return allocation


@pytest.fixture
def manager_team() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def allocation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def skill_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def timesheet_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(manager_team, allocation_repo, skill_repo, timesheet_repo):
    return ResourceDashboardService(
        manager_team, allocation_repo, skill_repo, timesheet_repo
    )


@pytest.mark.asyncio
async def test_get_resource_dashboard(service, manager_team, allocation_repo):
    bench = _resource(resource_id=2, skills=[_skill("Go")])
    manager_team.resolve_manager_resource_id.return_value = 100
    manager_team.list_bench_team_members.return_value = [bench]
    active = _resource(resource_id=1, name="Active Resource")
    allocation_repo.find_active_by_team.return_value = [
        _allocation(resource_id=1, utilisation=40, resource=active),
        _allocation(resource_id=1, utilisation=20, resource=active),
        _allocation(
            resource_id=3,
            utilisation=0,
            resource=_resource(resource_id=3, name="Zero"),
        ),
    ]

    result = await service.get_resource_dashboard(MagicMock())

    assert result.stats.bench_count == 1
    assert result.stats.partial_count == 1
    assert len(result.bench_resources) == 1
    assert result.bench_resources[0].skills == ["Go"]
    assert len(result.active_resources) == 1
    assert result.active_resources[0].utilisation_percent == 60
    assert "free" in result.active_resources[0].availability_label
    assert result.month_label


@pytest.mark.asyncio
async def test_dashboard_full_utilisation_label(
    service, manager_team, allocation_repo
):
    manager_team.resolve_manager_resource_id.return_value = 100
    manager_team.list_bench_team_members.return_value = []
    resource = _resource(resource_id=1, name="Full")
    allocation_repo.find_active_by_team.return_value = [
        _allocation(resource_id=1, utilisation=100, resource=resource),
    ]

    result = await service.get_resource_dashboard(MagicMock())

    assert result.active_resources[0].availability_label == "FULL"
    assert result.stats.partial_count == 0


@pytest.mark.asyncio
async def test_get_resource_detail(
    service, manager_team, allocation_repo, skill_repo, timesheet_repo
):
    manager_team.resolve_manager_resource_id.return_value = 100
    resource = _resource(resource_id=7, status="ALLOCATED")
    manager_team.get_team_member.return_value = resource
    skill_repo.find_by_resource_id.return_value = [_skill("Python")]
    allocation_repo.find_active_by_resource.return_value = [
        _allocation(resource_id=7, utilisation=80, project_name="Apollo"),
    ]
    timesheet_repo.find_recent_activity_tags.return_value = ["Coding"]

    result = await service.get_resource_detail(7, MagicMock())

    assert result.id == 7
    assert result.utilisation_percent == 80
    assert result.skills == ["Python"]
    assert result.active_allocations[0].project_name == "Apollo"
    assert result.recent_activity_tags == ["Coding"]


def test_sum_utilisation_by_resource():
    totals = ResourceDashboardService._sum_utilisation_by_resource(
        [
            SimpleNamespace(resource_id=1, utilisation_percent=30),
            SimpleNamespace(resource_id=1, utilisation_percent=20),
            SimpleNamespace(resource_id=2, utilisation_percent=10),
        ]
    )
    assert totals == {1: 50, 2: 10}
