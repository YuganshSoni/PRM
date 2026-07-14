from unittest.mock import AsyncMock, MagicMock

import pytest

from server.scheduler.scheduler_service import SchedulerService
from server.services.scheduler_results import (
    ComplianceRunResult,
    HealthFlagResult,
    MissedMarkResult,
    RecomputeResult,
    SchedulerRunResult,
)


@pytest.mark.asyncio
async def test_run_all_jobs_happy_path():
    session = AsyncMock()
    allocation_service = AsyncMock()
    allocation_service.recompute_all_resource_statuses.return_value = RecomputeResult(
        1, 2
    )
    timesheet_service = AsyncMock()
    timesheet_service.mark_missed_timesheets.return_value = MissedMarkResult(1, 0, 0)
    health_service = AsyncMock()
    health_service.flag_all_active_projects.return_value = HealthFlagResult(
        3, 1, 1, 1, [7]
    )
    at_risk = AsyncMock()
    at_risk.notify_project.return_value = True

    service = SchedulerService(
        session=session,
        allocation_service=allocation_service,
        timesheet_service=timesheet_service,
        project_health_service=health_service,
        at_risk_notification_service=at_risk,
    )

    result = await service.run_all_jobs()

    assert result.recompute.bench_count == 1
    assert result.missed.created == 1
    assert result.health.projects_processed == 3
    assert result.at_risk_emails_sent == 1
    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()
    at_risk.notify_project.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_run_all_jobs_rolls_back_on_error():
    session = AsyncMock()
    allocation_service = AsyncMock()
    allocation_service.recompute_all_resource_statuses.side_effect = RuntimeError(
        "fail"
    )
    service = SchedulerService(
        session=session,
        allocation_service=allocation_service,
        timesheet_service=AsyncMock(),
        project_health_service=AsyncMock(),
    )

    with pytest.raises(RuntimeError):
        await service.run_all_jobs()

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_all_jobs_skips_close_when_requested():
    session = AsyncMock()
    allocation_service = AsyncMock()
    allocation_service.recompute_all_resource_statuses.return_value = RecomputeResult(
        0, 0
    )
    timesheet_service = AsyncMock()
    timesheet_service.mark_missed_timesheets.return_value = MissedMarkResult(0, 0, 0)
    health_service = AsyncMock()
    health_service.flag_all_active_projects.return_value = HealthFlagResult(
        0, 0, 0, 0, []
    )
    service = SchedulerService(
        session=session,
        allocation_service=allocation_service,
        timesheet_service=timesheet_service,
        project_health_service=health_service,
    )

    await service.run_all_jobs(close_session=False)

    session.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_notify_at_risk_without_service_returns_zero():
    service = SchedulerService(
        session=AsyncMock(),
        allocation_service=AsyncMock(),
        timesheet_service=AsyncMock(),
        project_health_service=AsyncMock(),
        at_risk_notification_service=None,
    )
    assert await service._notify_at_risk_transitions([1, 2]) == 0


@pytest.mark.asyncio
async def test_notify_at_risk_counts_only_successful_sends():
    at_risk = AsyncMock()
    at_risk.notify_project.side_effect = [True, False, True]
    service = SchedulerService(
        session=AsyncMock(),
        allocation_service=AsyncMock(),
        timesheet_service=AsyncMock(),
        project_health_service=AsyncMock(),
        at_risk_notification_service=at_risk,
    )
    assert await service._notify_at_risk_transitions([1, 2, 3]) == 2


@pytest.mark.asyncio
async def test_run_daily_compliance_returns_none_without_service():
    service = SchedulerService(
        session=AsyncMock(),
        allocation_service=AsyncMock(),
        timesheet_service=AsyncMock(),
        project_health_service=AsyncMock(),
        compliance_service=None,
    )
    assert await service.run_daily_compliance() is None


@pytest.mark.asyncio
async def test_run_daily_compliance_happy_path():
    session = AsyncMock()
    compliance = AsyncMock()
    compliance.run_daily.return_value = ComplianceRunResult(
        reminders_sent=2, freezes_applied=1
    )
    service = SchedulerService(
        session=session,
        allocation_service=AsyncMock(),
        timesheet_service=AsyncMock(),
        project_health_service=AsyncMock(),
        compliance_service=compliance,
    )

    result = await service.run_daily_compliance()

    assert isinstance(result, SchedulerRunResult)
    assert result.compliance.reminders_sent == 2
    assert result.compliance.freezes_applied == 1
    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_daily_compliance_rolls_back_on_error():
    session = AsyncMock()
    compliance = AsyncMock()
    compliance.run_daily.side_effect = RuntimeError("fail")
    service = SchedulerService(
        session=session,
        allocation_service=AsyncMock(),
        timesheet_service=AsyncMock(),
        project_health_service=AsyncMock(),
        compliance_service=compliance,
    )

    with pytest.raises(RuntimeError):
        await service.run_daily_compliance()

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delegating_helpers():
    allocation_service = AsyncMock()
    timesheet_service = AsyncMock()
    health_service = AsyncMock()
    service = SchedulerService(
        session=AsyncMock(),
        allocation_service=allocation_service,
        timesheet_service=timesheet_service,
        project_health_service=health_service,
    )

    await service.recompute_utilisation()
    await service.mark_missed_timesheets()
    await service.flag_project_health()

    allocation_service.recompute_all_resource_statuses.assert_awaited_once()
    timesheet_service.mark_missed_timesheets.assert_awaited_once()
    health_service.flag_all_active_projects.assert_awaited_once()
