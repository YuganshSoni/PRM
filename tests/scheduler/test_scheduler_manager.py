from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.scheduler.scheduler_manager import (
    COMPLIANCE_JOB_ID,
    JOB_ID,
    SchedulerManager,
)


@pytest.mark.asyncio
async def test_start_and_reschedule():
    factory = AsyncMock()
    manager = SchedulerManager(factory)
    fake_scheduler = MagicMock()
    fake_scheduler.running = False
    fake_scheduler.get_job.return_value = None
    manager._scheduler = fake_scheduler

    await manager.start(6)

    fake_scheduler.start.assert_called_once()
    fake_scheduler.add_job.assert_called()
    assert manager._interval_hours == 6

    fake_scheduler.get_job.return_value = MagicMock()
    manager.reschedule(12)
    fake_scheduler.remove_job.assert_called_with(JOB_ID)
    assert manager._interval_hours == 12


@pytest.mark.asyncio
async def test_shutdown_when_running():
    manager = SchedulerManager(AsyncMock())
    fake_scheduler = MagicMock()
    fake_scheduler.running = True
    manager._scheduler = fake_scheduler

    await manager.shutdown()

    fake_scheduler.shutdown.assert_called_once_with(wait=False)


@pytest.mark.asyncio
async def test_shutdown_when_not_running():
    manager = SchedulerManager(AsyncMock())
    fake_scheduler = MagicMock()
    fake_scheduler.running = False
    manager._scheduler = fake_scheduler

    await manager.shutdown()

    fake_scheduler.shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_job_wrapper_runs_jobs():
    sched_service = AsyncMock()
    factory = AsyncMock(return_value=sched_service)
    manager = SchedulerManager(factory)

    await manager._job_wrapper()

    factory.assert_awaited_once()
    sched_service.run_all_jobs.assert_awaited_once()


@pytest.mark.asyncio
async def test_job_wrapper_swallows_errors():
    factory = AsyncMock(side_effect=RuntimeError("boom"))
    manager = SchedulerManager(factory)
    await manager._job_wrapper()


def test_register_compliance_job_skipped_without_factory():
    manager = SchedulerManager(AsyncMock(), compliance_factory=None)
    fake_scheduler = MagicMock()
    manager._scheduler = fake_scheduler
    manager._register_compliance_job()
    fake_scheduler.add_job.assert_not_called()


def test_register_compliance_job_adds_cron():
    manager = SchedulerManager(AsyncMock(), compliance_factory=AsyncMock())
    fake_scheduler = MagicMock()
    fake_scheduler.get_job.return_value = MagicMock()
    manager._scheduler = fake_scheduler

    with patch("apscheduler.triggers.cron.CronTrigger") as cron:
        cron.return_value = MagicMock()
        manager._register_compliance_job()

    fake_scheduler.remove_job.assert_called_with(COMPLIANCE_JOB_ID)
    fake_scheduler.add_job.assert_called_once()


@pytest.mark.asyncio
async def test_compliance_job_wrapper():
    sched_service = AsyncMock()
    compliance_factory = AsyncMock(return_value=sched_service)
    manager = SchedulerManager(AsyncMock(), compliance_factory=compliance_factory)

    await manager._compliance_job_wrapper()

    sched_service.run_daily_compliance.assert_awaited_once()


@pytest.mark.asyncio
async def test_compliance_job_wrapper_no_factory():
    manager = SchedulerManager(AsyncMock(), compliance_factory=None)
    await manager._compliance_job_wrapper()


@pytest.mark.asyncio
async def test_compliance_job_wrapper_swallows_errors():
    compliance_factory = AsyncMock(side_effect=RuntimeError("boom"))
    manager = SchedulerManager(AsyncMock(), compliance_factory=compliance_factory)
    await manager._compliance_job_wrapper()
