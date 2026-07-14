import logging

from sqlalchemy.ext.asyncio import AsyncSession

from server.notifications.services.at_risk_notification_service import (
    AtRiskNotificationService,
)
from server.services.allocation_service import AllocationService
from server.services.project_health_service import ProjectHealthService
from server.services.scheduler_results import SchedulerRunResult
from server.services.timesheet_compliance_service import TimesheetComplianceService
from server.services.timesheet_service import TimesheetService

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        allocation_service: AllocationService,
        timesheet_service: TimesheetService,
        project_health_service: ProjectHealthService,
        compliance_service: TimesheetComplianceService | None = None,
        at_risk_notification_service: AtRiskNotificationService | None = None,
    ) -> None:
        self._session = session
        self._allocation_service = allocation_service
        self._timesheet_service = timesheet_service
        self._project_health_service = project_health_service
        self._compliance_service = compliance_service
        self._at_risk_notification_service = at_risk_notification_service

    async def run_all_jobs(self, *, close_session: bool = True) -> SchedulerRunResult:
        try:
            recompute = await self.recompute_utilisation()
            missed = await self.mark_missed_timesheets()
            health = await self.flag_project_health()
            at_risk_emails_sent = await self._notify_at_risk_transitions(
                health.at_risk_transitions
            )
            await self._session.commit()
            logger.info(
                "Scheduler run complete: bench=%s allocated=%s missed_created=%s "
                "projects=%s at_risk_emails=%s",
                recompute.bench_count,
                recompute.allocated_count,
                missed.created,
                health.projects_processed,
                at_risk_emails_sent,
            )
            return SchedulerRunResult(
                recompute=recompute,
                missed=missed,
                health=health,
                at_risk_emails_sent=at_risk_emails_sent,
            )
        except Exception:
            await self._session.rollback()
            raise
        finally:
            if close_session:
                await self._session.close()

    async def run_daily_compliance(
        self, *, close_session: bool = True
    ) -> SchedulerRunResult | None:
        if self._compliance_service is None:
            return None
        try:
            compliance = await self._compliance_service.run_daily()
            await self._session.commit()
            logger.info(
                "Compliance job complete: reminders=%s freezes=%s",
                compliance.reminders_sent,
                compliance.freezes_applied,
            )
            from server.services.scheduler_results import (
                ComplianceRunResult,
                HealthFlagResult,
                MissedMarkResult,
                RecomputeResult,
            )

            return SchedulerRunResult(
                recompute=RecomputeResult(0, 0),
                missed=MissedMarkResult(0, 0, 0),
                health=HealthFlagResult(0, 0, 0, 0, []),
                compliance=compliance,
            )
        except Exception:
            await self._session.rollback()
            raise
        finally:
            if close_session:
                await self._session.close()

    async def recompute_utilisation(self):
        return await self._allocation_service.recompute_all_resource_statuses()

    async def mark_missed_timesheets(self):
        return await self._timesheet_service.mark_missed_timesheets()

    async def flag_project_health(self):
        return await self._project_health_service.flag_all_active_projects()

    async def _notify_at_risk_transitions(self, project_ids: list[int]) -> int:
        if self._at_risk_notification_service is None:
            return 0
        sent = 0
        for project_id in project_ids:
            if await self._at_risk_notification_service.notify_project(project_id):
                sent += 1
        return sent
