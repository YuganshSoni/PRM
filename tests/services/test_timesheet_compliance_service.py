from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.core.exceptions import (
    ComplianceRecordNotFoundError,
    EmployeeNotAllocatableError,
    ManagerProfileNotFoundError,
)
from server.core.working_day_calendar import WorkingDayCalendar
from server.models.enums import TimesheetComplianceStatus, TimesheetStatus
from server.services.timesheet_compliance_service import TimesheetComplianceService


@pytest.fixture
def compliance_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def timesheet_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def allocation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def resource_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def notification_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    compliance_repo,
    timesheet_repo,
    allocation_repo,
    resource_repo,
    notification_service,
) -> TimesheetComplianceService:
    return TimesheetComplianceService(
        compliance_repo,
        timesheet_repo,
        allocation_repo,
        resource_repo,
        notification_service,
    )


def _resource(
    *,
    resource_id: int = 10,
    manager_id: int = 100,
    active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=resource_id,
        is_active=active,
        manager_id=manager_id,
        user=SimpleNamespace(
            email="res@example.com",
            full_name="Res User",
        ),
    )


@pytest.mark.asyncio
async def test_is_submission_frozen(service, compliance_repo):
    compliance_repo.find_frozen_by_resource.return_value = SimpleNamespace(id=1)
    assert await service.is_submission_frozen(10) is True

    compliance_repo.find_frozen_by_resource.return_value = None
    assert await service.is_submission_frozen(10) is False


@pytest.mark.asyncio
async def test_run_daily_skips_submitted_timesheet(
    service, allocation_repo, resource_repo, timesheet_repo, notification_service
):
    week_start = date(2026, 7, 6)
    today = WorkingDayCalendar.reminder_1_day(week_start)
    allocation_repo.find_overlapping_week.return_value = [
        SimpleNamespace(resource_id=10)
    ]
    resource_repo.get_by_id_with_user.return_value = _resource()
    timesheet_repo.find_by_resource_and_week.return_value = SimpleNamespace(
        status=TimesheetStatus.SUBMITTED
    )

    result = await service.run_daily(today=today)

    assert result.reminders_sent == 0
    assert result.freezes_applied == 0
    notification_service.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_daily_sends_reminder_1(
    service,
    allocation_repo,
    resource_repo,
    timesheet_repo,
    compliance_repo,
    notification_service,
):
    week_start = date(2026, 7, 6)
    today = WorkingDayCalendar.reminder_1_day(week_start)
    allocation_repo.find_overlapping_week.return_value = [
        SimpleNamespace(resource_id=10)
    ]
    resource_repo.get_by_id_with_user.return_value = _resource()
    timesheet_repo.find_by_resource_and_week.return_value = None
    record = SimpleNamespace(
        status=TimesheetComplianceStatus.PENDING,
        reminder_1_sent_at=None,
    )
    compliance_repo.find_by_resource_and_week.return_value = record
    compliance_repo.save.return_value = record

    result = await service.run_daily(today=today)

    assert result.reminders_sent == 1
    assert record.status == TimesheetComplianceStatus.REMINDER_1_SENT
    notification_service.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_daily_sends_reminder_2(
    service,
    allocation_repo,
    resource_repo,
    timesheet_repo,
    compliance_repo,
    notification_service,
):
    week_start = date(2026, 7, 6)
    today = WorkingDayCalendar.reminder_2_day(week_start)
    allocation_repo.find_overlapping_week.return_value = [
        SimpleNamespace(resource_id=10)
    ]
    resource_repo.get_by_id_with_user.return_value = _resource()
    timesheet_repo.find_by_resource_and_week.return_value = None
    record = SimpleNamespace(
        status=TimesheetComplianceStatus.REMINDER_1_SENT,
        reminder_2_sent_at=None,
    )
    compliance_repo.find_by_resource_and_week.return_value = record
    compliance_repo.save.return_value = record

    result = await service.run_daily(today=today)

    assert result.reminders_sent == 1
    assert record.status == TimesheetComplianceStatus.REMINDER_2_SENT
    notification_service.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_daily_applies_freeze(
    service,
    allocation_repo,
    resource_repo,
    timesheet_repo,
    compliance_repo,
    notification_service,
):
    week_start = date(2026, 7, 6)
    today = WorkingDayCalendar.freeze_day(week_start)
    allocation_repo.find_overlapping_week.return_value = [
        SimpleNamespace(resource_id=10)
    ]
    resource = _resource()
    resource_repo.get_by_id_with_user.side_effect = [
        resource,  # allocated resource
        SimpleNamespace(  # manager for name/email
            id=100,
            user=SimpleNamespace(email="mgr@example.com", full_name="Mgr"),
        ),
        SimpleNamespace(
            id=100,
            user=SimpleNamespace(email="mgr@example.com", full_name="Mgr"),
        ),
    ]
    timesheet_repo.find_by_resource_and_week.return_value = None
    record = SimpleNamespace(
        status=TimesheetComplianceStatus.REMINDER_2_SENT,
        frozen_at=None,
    )
    compliance_repo.find_by_resource_and_week.return_value = record
    compliance_repo.save.return_value = record

    result = await service.run_daily(today=today)

    assert result.freezes_applied == 1
    assert record.status == TimesheetComplianceStatus.FROZEN
    assert notification_service.send.await_count == 2


@pytest.mark.asyncio
async def test_restore_access_requires_team_member(service, resource_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=100)
    resource_repo.get_by_id_with_user.return_value = _resource(manager_id=999)
    with pytest.raises(EmployeeNotAllocatableError):
        await service.restore_access(
            SimpleNamespace(id=1), resource_id=10, week_start=date(2026, 7, 6)
        )


@pytest.mark.asyncio
async def test_restore_access_requires_frozen_record(
    service, resource_repo, compliance_repo
):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=100)
    resource_repo.get_by_id_with_user.return_value = _resource(manager_id=100)
    compliance_repo.find_by_resource_and_week.return_value = SimpleNamespace(
        status=TimesheetComplianceStatus.PENDING
    )
    with pytest.raises(ComplianceRecordNotFoundError):
        await service.restore_access(
            SimpleNamespace(id=1), resource_id=10, week_start=date(2026, 7, 6)
        )


@pytest.mark.asyncio
async def test_restore_access_happy_path(service, resource_repo, compliance_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=100)
    resource_repo.get_by_id_with_user.return_value = _resource(manager_id=100)
    record = SimpleNamespace(
        status=TimesheetComplianceStatus.FROZEN,
        restored_at=None,
        restored_by_manager_id=None,
    )
    compliance_repo.find_by_resource_and_week.return_value = record
    compliance_repo.save.return_value = record

    result = await service.restore_access(
        SimpleNamespace(id=1), resource_id=10, week_start=date(2026, 7, 6)
    )

    assert result.status == TimesheetComplianceStatus.RESTORED
    assert result.restored_by_manager_id == 100


@pytest.mark.asyncio
async def test_mark_submitted_updates_existing_record(service, compliance_repo):
    record = SimpleNamespace(status=TimesheetComplianceStatus.PENDING)
    compliance_repo.find_by_resource_and_week.return_value = record
    await service.mark_submitted(10, date(2026, 7, 6))
    assert record.status == TimesheetComplianceStatus.SUBMITTED
    compliance_repo.save.assert_awaited_once_with(record)


@pytest.mark.asyncio
async def test_resolve_manager_missing_profile(service, resource_repo):
    resource_repo.find_by_user_id.return_value = None
    with pytest.raises(ManagerProfileNotFoundError):
        await service._resolve_manager_resource_id(SimpleNamespace(id=1))
