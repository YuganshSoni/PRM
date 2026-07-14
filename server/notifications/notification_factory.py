from sqlalchemy.ext.asyncio import AsyncSession

from server.ai.services.project_facts_service import ProjectFactsService
from server.ai.services.team_build_candidate_service import TeamBuildCandidateService
from server.services.manager_team_service import ManagerTeamService
from server.notifications.services.allocation_notification_service import (
    AllocationNotificationService,
)
from server.notifications.services.at_risk_help_suggestion_service import (
    AtRiskHelpSuggestionService,
)
from server.notifications.services.at_risk_notification_service import (
    AtRiskNotificationService,
)
from server.notifications.services.notification_service import NotificationService
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.notification_log_repository import NotificationLogRepository
from server.repositories.project_health_repository import ProjectHealthRepository
from server.repositories.project_repository import ProjectRepository
from server.repositories.project_risk_flag_repository import ProjectRiskFlagRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.system_config_repository import SystemConfigRepository
from server.repositories.timesheet_compliance_repository import (
    TimesheetComplianceRepository,
)
from server.repositories.timesheet_repository import TimesheetRepository
from server.services.project_health_service import ProjectHealthService
from server.services.timesheet_compliance_service import TimesheetComplianceService


class NotificationBundle:
    def __init__(
        self,
        notification_service: NotificationService,
        allocation_notification_service: AllocationNotificationService,
        compliance_service: TimesheetComplianceService,
        at_risk_notification_service: AtRiskNotificationService,
    ) -> None:
        self.notification_service = notification_service
        self.allocation_notification_service = allocation_notification_service
        self.compliance_service = compliance_service
        self.at_risk_notification_service = at_risk_notification_service


def build_notification_bundle(
    session: AsyncSession,
    *,
    project_health_service: ProjectHealthService | None = None,
) -> NotificationBundle:
    system_config_repository = SystemConfigRepository(session)
    notification_service = NotificationService(
        config_repository=system_config_repository,
        log_repository=NotificationLogRepository(session),
    )
    allocation_notification_service = AllocationNotificationService(
        notification_service
    )

    resource_repository = ResourceRepository(session)
    timesheet_repository = TimesheetRepository(session)
    allocation_repository = AllocationRepository(session)
    project_repository = ProjectRepository(session)

    compliance_service = TimesheetComplianceService(
        compliance_repository=TimesheetComplianceRepository(session),
        timesheet_repository=timesheet_repository,
        allocation_repository=allocation_repository,
        resource_repository=resource_repository,
        notification_service=notification_service,
    )

    bench_service = TeamBuildCandidateService(
        manager_team_service=ManagerTeamService(resource_repository),
        timesheet_repository=timesheet_repository,
    )
    help_service = AtRiskHelpSuggestionService(
        project_repository=project_repository,
        bench_candidate_service=bench_service,
    )
    facts_service = ProjectFactsService(
        project_repository=project_repository,
        milestone_repository=MilestoneRepository(session),
        allocation_repository=allocation_repository,
        project_health_service=project_health_service
        or ProjectHealthService(
            project_repository=project_repository,
            milestone_repository=MilestoneRepository(session),
            allocation_repository=allocation_repository,
            timesheet_repository=timesheet_repository,
            project_health_repository=ProjectHealthRepository(session),
            project_risk_flag_repository=ProjectRiskFlagRepository(session),
            system_config_repository=system_config_repository,
        ),
    )
    at_risk_notification_service = AtRiskNotificationService(
        project_repository=project_repository,
        milestone_repository=MilestoneRepository(session),
        project_facts_service=facts_service,
        help_suggestion_service=help_service,
        notification_service=notification_service,
    )

    return NotificationBundle(
        notification_service=notification_service,
        allocation_notification_service=allocation_notification_service,
        compliance_service=compliance_service,
        at_risk_notification_service=at_risk_notification_service,
    )
