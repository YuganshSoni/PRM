from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from server.core.exceptions import SystemConfigNotFoundError
from server.models.enums import HealthStatus, MilestoneStatus
from server.services.project_health_service import ProjectHealthService

_FIXED_TODAY = date(2026, 7, 14)


@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def milestone_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def allocation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def timesheet_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def health_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def risk_flag_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def system_config_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    project_repo,
    milestone_repo,
    allocation_repo,
    timesheet_repo,
    health_repo,
    risk_flag_repo,
    system_config_repo,
) -> ProjectHealthService:
    return ProjectHealthService(
        project_repo,
        milestone_repo,
        allocation_repo,
        timesheet_repo,
        health_repo,
        risk_flag_repo,
        system_config_repo,
    )


@pytest.mark.asyncio
async def test_get_snapshot_none(service, health_repo):
    health_repo.find_by_project_id.return_value = None
    assert await service.get_snapshot(1) is None


@pytest.mark.asyncio
async def test_get_snapshot_maps_row(service, health_repo):
    health_repo.find_by_project_id.return_value = SimpleNamespace(
        health_status=HealthStatus.ON_TRACK,
        computed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    snap = await service.get_snapshot(1)
    assert snap is not None
    assert snap.health_status == HealthStatus.ON_TRACK


@pytest.mark.asyncio
async def test_get_risk_flags_empty_without_health(service, health_repo):
    health_repo.find_by_project_id.return_value = None
    assert await service.get_risk_flags_for_project(1) == []


@pytest.mark.asyncio
async def test_compute_health_requires_config(service, system_config_repo):
    system_config_repo.get.return_value = None
    with pytest.raises(SystemConfigNotFoundError):
        await service.compute_health(1)


@pytest.mark.asyncio
async def test_compute_health_on_track(
    service, system_config_repo, milestone_repo, allocation_repo, timesheet_repo
):
    system_config_repo.get.return_value = SimpleNamespace(max_weekly_hours=40)
    milestone_repo.find_by_project_id.return_value = []
    allocation_repo.find_active_for_project_in_week.return_value = []
    timesheet_repo.sum_hours_by_project_and_week.return_value = {}

    with patch(
        "server.services.project_health_service.date"
    ) as mock_date:
        mock_date.today.return_value = _FIXED_TODAY
        result = await service.compute_health(1)

    assert result.health_status == HealthStatus.ON_TRACK
    assert result.risk_flags == []


@pytest.mark.asyncio
async def test_compute_health_attention_for_overdue_milestone(
    service, system_config_repo, milestone_repo, allocation_repo, timesheet_repo
):
    system_config_repo.get.return_value = SimpleNamespace(max_weekly_hours=40)
    milestone_repo.find_by_project_id.return_value = [
        SimpleNamespace(
            title="Sprint 1",
            due_date=date(2026, 7, 1),
            status=MilestoneStatus.IN_PROGRESS,
        )
    ]
    allocation_repo.find_active_for_project_in_week.return_value = []
    timesheet_repo.sum_hours_by_project_and_week.return_value = {}

    with patch(
        "server.services.project_health_service.date"
    ) as mock_date:
        mock_date.today.return_value = _FIXED_TODAY
        result = await service.compute_health(1)

    assert result.health_status == HealthStatus.ATTENTION
    assert any("overdue" in flag.flag_text for flag in result.risk_flags)


@pytest.mark.asyncio
async def test_compute_health_at_risk_when_overdue_and_severe_low_hours(
    service, system_config_repo, milestone_repo, allocation_repo, timesheet_repo
):
    system_config_repo.get.return_value = SimpleNamespace(max_weekly_hours=40)
    milestone_repo.find_by_project_id.return_value = [
        SimpleNamespace(
            title="Sprint 1",
            due_date=date(2026, 7, 1),
            status=MilestoneStatus.IN_PROGRESS,
        )
    ]
    allocation_repo.find_active_for_project_in_week.return_value = [
        SimpleNamespace(
            resource_id=10,
            utilisation_percent=100,
            resource=SimpleNamespace(
                user=SimpleNamespace(full_name="Alex")
            ),
        )
    ]
    # expected 40h; logged 5h < 25% => severe
    timesheet_repo.sum_hours_by_project_and_week.return_value = {
        10: Decimal("5")
    }

    with patch(
        "server.services.project_health_service.date"
    ) as mock_date:
        mock_date.today.return_value = _FIXED_TODAY
        result = await service.compute_health(1)

    assert result.health_status == HealthStatus.AT_RISK
    assert any(flag.is_positive for flag in result.risk_flags)


@pytest.mark.asyncio
async def test_compute_and_persist_detects_transition(
    service, health_repo, risk_flag_repo, system_config_repo, milestone_repo,
    allocation_repo, timesheet_repo,
):
    system_config_repo.get.return_value = SimpleNamespace(max_weekly_hours=40)
    milestone_repo.find_by_project_id.return_value = [
        SimpleNamespace(
            title="Sprint 1",
            due_date=date(2026, 7, 1),
            status=MilestoneStatus.IN_PROGRESS,
        )
    ]
    allocation_repo.find_active_for_project_in_week.return_value = [
        SimpleNamespace(
            resource_id=10,
            utilisation_percent=100,
            resource=SimpleNamespace(user=SimpleNamespace(full_name="Alex")),
        )
    ]
    timesheet_repo.sum_hours_by_project_and_week.return_value = {10: Decimal("5")}

    existing = SimpleNamespace(
        id=50,
        health_status=HealthStatus.ON_TRACK,
        computed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    health_repo.find_by_project_id.return_value = existing
    health_repo.save.return_value = existing
    risk_flag_repo.delete_by_health_id.return_value = None
    risk_flag_repo.save_all.return_value = None

    with patch(
        "server.services.project_health_service.date"
    ) as mock_date:
        mock_date.today.return_value = _FIXED_TODAY
        result = await service.compute_and_persist_health(1)

    assert result.transitioned_to_at_risk is True
    assert existing.health_status == HealthStatus.AT_RISK
