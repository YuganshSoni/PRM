from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from server.notifications.notification_wiring import build_notification_bundle
from server.repositories.activity_tag_repository import ActivityTagRepository
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_health_repository import ProjectHealthRepository
from server.repositories.project_repository import ProjectRepository
from server.repositories.project_risk_flag_repository import ProjectRiskFlagRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.resource_status_repository import ResourceStatusRepository
from server.repositories.system_config_repository import SystemConfigRepository
from server.repositories.timesheet_entry_repository import TimesheetEntryRepository
from server.repositories.timesheet_entry_tag_repository import TimesheetEntryTagRepository
from server.repositories.timesheet_repository import TimesheetRepository
from server.scheduler.scheduler_service import SchedulerService
from server.services.allocation_service import AllocationService
from server.services.project_health_service import ProjectHealthService
from server.services.timesheet_service import TimesheetService


class SchedulerServiceFactory:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_factory = session_factory

    async def create(self) -> SchedulerService:
        session = self._session_factory()
        bundle = build_notification_bundle(session)
        allocation_repository = AllocationRepository(session)
        resource_repository = ResourceRepository(session)
        resource_status_repository = ResourceStatusRepository(session)
        project_repository = ProjectRepository(session)
        system_config_repository = SystemConfigRepository(session)
        timesheet_repository = TimesheetRepository(session)

        allocation_service = AllocationService(
            resource_repository=resource_repository,
            project_repository=project_repository,
            allocation_repository=allocation_repository,
            system_config_repository=system_config_repository,
            resource_status_repository=resource_status_repository,
            allocation_notification_service=bundle.allocation_notification_service,
        )
        timesheet_service = TimesheetService(
            timesheet_repository=timesheet_repository,
            timesheet_entry_repository=TimesheetEntryRepository(session),
            timesheet_entry_tag_repository=TimesheetEntryTagRepository(session),
            activity_tag_repository=ActivityTagRepository(session),
            allocation_repository=allocation_repository,
            resource_repository=resource_repository,
            system_config_repository=system_config_repository,
            compliance_service=bundle.compliance_service,
        )
        project_health_service = ProjectHealthService(
            project_repository=project_repository,
            milestone_repository=MilestoneRepository(session),
            allocation_repository=allocation_repository,
            timesheet_repository=timesheet_repository,
            project_health_repository=ProjectHealthRepository(session),
            project_risk_flag_repository=ProjectRiskFlagRepository(session),
            system_config_repository=system_config_repository,
        )
        return SchedulerService(
            session=session,
            allocation_service=allocation_service,
            timesheet_service=timesheet_service,
            project_health_service=project_health_service,
            compliance_service=bundle.compliance_service,
            at_risk_notification_service=bundle.at_risk_notification_service,
        )
