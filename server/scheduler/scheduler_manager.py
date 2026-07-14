import logging
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from server.scheduler.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

JOB_ID = "prm_scheduled_maintenance"
COMPLIANCE_JOB_ID = "prm_timesheet_compliance_daily"


class SchedulerManager:
    def __init__(
        self,
        service_factory: Callable[[], Awaitable[SchedulerService]],
        compliance_factory: Callable[[], Awaitable[SchedulerService]] | None = None,
    ) -> None:
        self._service_factory = service_factory
        self._compliance_factory = compliance_factory
        self._scheduler = AsyncIOScheduler()
        self._interval_hours: int | None = None

    async def start(self, interval_hours: int) -> None:
        self._interval_hours = interval_hours
        if not self._scheduler.running:
            self._scheduler.start()
        self.reschedule(interval_hours)
        self._register_compliance_job()
        logger.info("Scheduler started (interval=%sh)", interval_hours)

    async def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down")

    def reschedule(self, interval_hours: int) -> None:
        self._interval_hours = interval_hours
        if self._scheduler.get_job(JOB_ID) is not None:
            self._scheduler.remove_job(JOB_ID)
        self._scheduler.add_job(
            self._job_wrapper,
            trigger=IntervalTrigger(hours=interval_hours),
            id=JOB_ID,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        logger.info("Scheduler rescheduled (interval=%sh)", interval_hours)

    async def _job_wrapper(self) -> None:
        try:
            scheduler_service = await self._service_factory()
            await scheduler_service.run_all_jobs()
        except Exception:
            logger.exception("Scheduler job failed")

    def _register_compliance_job(self) -> None:
        if self._compliance_factory is None:
            return
        from apscheduler.triggers.cron import CronTrigger

        if self._scheduler.get_job(COMPLIANCE_JOB_ID) is not None:
            self._scheduler.remove_job(COMPLIANCE_JOB_ID)
        self._scheduler.add_job(
            self._compliance_job_wrapper,
            trigger=CronTrigger(day_of_week="mon-fri", hour=9, minute=0),
            id=COMPLIANCE_JOB_ID,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )

    async def _compliance_job_wrapper(self) -> None:
        if self._compliance_factory is None:
            return
        try:
            scheduler_service = await self._compliance_factory()
            await scheduler_service.run_daily_compliance()
        except Exception:
            logger.exception("Timesheet compliance job failed")
