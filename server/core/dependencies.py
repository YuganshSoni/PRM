from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.core.database import get_db
from server.core.exceptions import ForbiddenError, InvalidTokenError, UserNotFoundError
from server.core.jwt_token_service import JwtTokenService
from server.core.user_role import user_role_enum
from server.core.password_policy import PasswordPolicy
from server.core.security import PasswordHasher
from server.models.enums import UserRole
from server.models.user import User
from server.core.api_key_masker import ApiKeyMasker
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_health_repository import ProjectHealthRepository
from server.repositories.project_repository import ProjectRepository
from server.repositories.project_risk_flag_repository import ProjectRiskFlagRepository
from server.repositories.master_skill_repository import MasterSkillRepository
from server.repositories.skill_repository import SkillRepository
from server.repositories.system_config_repository import SystemConfigRepository
from server.repositories.activity_tag_repository import ActivityTagRepository
from server.repositories.timesheet_entry_repository import TimesheetEntryRepository
from server.repositories.timesheet_entry_tag_repository import TimesheetEntryTagRepository
from server.repositories.timesheet_repository import TimesheetRepository
from server.repositories.department_repository import DepartmentRepository
from server.repositories.designation_repository import DesignationRepository
from server.repositories.resource_status_repository import ResourceStatusRepository
from server.repositories.role_repository import RoleRepository
from server.repositories.user_repository import UserRepository
from server.ai.llm_factory import LLMFactory
from server.ai.services.project_facts_service import ProjectFactsService
from server.ai.services.skill_match_candidate_service import SkillMatchCandidateService
from server.ai.services.availability_date_service import AvailabilityDateService
from server.ai.services.team_build_candidate_service import TeamBuildCandidateService
from server.ai.services.team_diagnostics_service import TeamDiagnosticsService
from server.ai.services.team_gap_analyzer import TeamGapAnalyzer
from server.services.activity_tag_service import ActivityTagService
from server.services.ai_service import AIService
from server.services.allocation_service import AllocationService
from server.services.allocation_view_service import AllocationViewService
from server.services.auth_service import AuthService
from server.services.resource_service import EmployeeService
from server.services.milestone_service import MilestoneService
from server.services.project_health_service import ProjectHealthService
from server.services.project_service import ProjectService
from server.services.skill_service import SkillService
from server.services.resource_dashboard_service import ResourceDashboardService
from server.services.system_config_service import SystemConfigService
from server.services.timesheet_service import TimesheetService
from server.services.user_service import UserService
from server.notifications.notification_wiring import build_notification_bundle


class DependencyProvider:
    """FastAPI dependency wiring for auth and future routes.

    Routes exempt from ``require_password_changed``: change-password, logout, me.
    """

    async def get_user_repository(
        self, session: AsyncSession = Depends(get_db)
    ) -> UserRepository:
        return UserRepository(session)

    async def get_jwt_token_service(self) -> JwtTokenService:
        return JwtTokenService(get_settings())

    def require_role(self, *roles: UserRole) -> Callable[..., User]:
        allowed = set(roles)

        async def _guard(
            user: Annotated[User, Depends(dependency_provider.get_current_user)],
        ) -> User:
            if user_role_enum(user) not in allowed:
                raise ForbiddenError("Insufficient permissions")
            return user

        return _guard


dependency_provider = DependencyProvider()


async def get_current_user(
    user_repository: Annotated[
        UserRepository, Depends(dependency_provider.get_user_repository)
    ],
    jwt_token_service: Annotated[
        JwtTokenService, Depends(dependency_provider.get_jwt_token_service)
    ],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise InvalidTokenError("Missing or invalid authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise InvalidTokenError("Missing or invalid authorization header")

    payload = jwt_token_service.decode_access_token(token)
    user = await user_repository.find_by_id(payload.sub)
    if user is None:
        raise UserNotFoundError("User not found")

    return user


dependency_provider.get_current_user = get_current_user


async def get_auth_service(
    user_repository: Annotated[
        UserRepository, Depends(dependency_provider.get_user_repository)
    ],
    jwt_token_service: Annotated[
        JwtTokenService, Depends(dependency_provider.get_jwt_token_service)
    ],
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        password_hasher=PasswordHasher(),
        jwt_token_service=jwt_token_service,
        password_policy=PasswordPolicy(),
    )


dependency_provider.get_auth_service = get_auth_service


async def require_password_changed(
    user: Annotated[User, Depends(dependency_provider.get_current_user)],
) -> User:
    if user.force_password_change:
        raise ForbiddenError(
            "Password change required before accessing this resource"
        )
    return user


dependency_provider.require_password_changed = require_password_changed


async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_repository: Annotated[
        UserRepository, Depends(dependency_provider.get_user_repository)
    ],
    auth_service: Annotated[AuthService, Depends(dependency_provider.get_auth_service)],
) -> UserService:
    return UserService(
        user_repository=user_repository,
        role_repository=RoleRepository(session),
        password_hasher=PasswordHasher(),
        auth_service=auth_service,
    )


dependency_provider.get_user_service = get_user_service


async def get_resource_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_repository: Annotated[
        UserRepository, Depends(dependency_provider.get_user_repository)
    ],
) -> EmployeeService:
    return EmployeeService(
        resource_repository=ResourceRepository(session),
        user_repository=user_repository,
        allocation_repository=AllocationRepository(session),
        department_repository=DepartmentRepository(session),
        designation_repository=DesignationRepository(session),
        resource_status_repository=ResourceStatusRepository(session),
    )


dependency_provider.get_resource_service = get_resource_service


async def get_skill_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SkillService:
    return SkillService(
        skill_repository=SkillRepository(session),
        resource_repository=ResourceRepository(session),
        master_skill_repository=MasterSkillRepository(session),
    )


dependency_provider.get_skill_service = get_skill_service


async def get_project_health_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectHealthService:
    return ProjectHealthService(
        project_repository=ProjectRepository(session),
        milestone_repository=MilestoneRepository(session),
        allocation_repository=AllocationRepository(session),
        timesheet_repository=TimesheetRepository(session),
        project_health_repository=ProjectHealthRepository(session),
        project_risk_flag_repository=ProjectRiskFlagRepository(session),
        system_config_repository=SystemConfigRepository(session),
    )


dependency_provider.get_project_health_service = get_project_health_service


async def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    project_health_service: Annotated[
        ProjectHealthService, Depends(dependency_provider.get_project_health_service)
    ],
) -> ProjectService:
    return ProjectService(
        project_repository=ProjectRepository(session),
        resource_repository=ResourceRepository(session),
        milestone_repository=MilestoneRepository(session),
        allocation_repository=AllocationRepository(session),
        project_health_service=project_health_service,
    )


dependency_provider.get_project_service = get_project_service


async def get_milestone_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MilestoneService:
    return MilestoneService(
        milestone_repository=MilestoneRepository(session),
        project_repository=ProjectRepository(session),
    )


dependency_provider.get_milestone_service = get_milestone_service


async def get_system_config_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SystemConfigService:
    return SystemConfigService(
        config_repository=SystemConfigRepository(session),
        api_key_masker=ApiKeyMasker(),
    )


dependency_provider.get_system_config_service = get_system_config_service


async def get_allocation_view_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AllocationViewService:
    return AllocationViewService(
        allocation_repository=AllocationRepository(session),
    )


dependency_provider.get_allocation_view_service = get_allocation_view_service


async def get_resource_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ResourceDashboardService:
    return ResourceDashboardService(
        resource_repository=ResourceRepository(session),
        allocation_repository=AllocationRepository(session),
        skill_repository=SkillRepository(session),
        timesheet_repository=TimesheetRepository(session),
    )


dependency_provider.get_resource_dashboard_service = get_resource_dashboard_service


async def get_allocation_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AllocationService:
    bundle = build_notification_bundle(session)
    return AllocationService(
        resource_repository=ResourceRepository(session),
        project_repository=ProjectRepository(session),
        allocation_repository=AllocationRepository(session),
        system_config_repository=SystemConfigRepository(session),
        resource_status_repository=ResourceStatusRepository(session),
        allocation_notification_service=bundle.allocation_notification_service,
    )


dependency_provider.get_allocation_service = get_allocation_service


async def get_timesheet_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TimesheetService:
    bundle = build_notification_bundle(session)
    return TimesheetService(
        timesheet_repository=TimesheetRepository(session),
        timesheet_entry_repository=TimesheetEntryRepository(session),
        timesheet_entry_tag_repository=TimesheetEntryTagRepository(session),
        activity_tag_repository=ActivityTagRepository(session),
        allocation_repository=AllocationRepository(session),
        resource_repository=ResourceRepository(session),
        system_config_repository=SystemConfigRepository(session),
        compliance_service=bundle.compliance_service,
    )


async def get_timesheet_compliance_service(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return build_notification_bundle(session).compliance_service


dependency_provider.get_timesheet_compliance_service = get_timesheet_compliance_service


dependency_provider.get_timesheet_service = get_timesheet_service


async def get_activity_tag_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ActivityTagService:
    return ActivityTagService(
        activity_tag_repository=ActivityTagRepository(session),
    )


dependency_provider.get_activity_tag_service = get_activity_tag_service


async def get_ai_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    system_config_service: Annotated[
        SystemConfigService, Depends(dependency_provider.get_system_config_service)
    ],
    project_health_service: Annotated[
        ProjectHealthService, Depends(dependency_provider.get_project_health_service)
    ],
) -> AIService:
    resource_repository = ResourceRepository(session)
    allocation_repository = AllocationRepository(session)
    timesheet_repository = TimesheetRepository(session)
    availability_date_service = AvailabilityDateService(allocation_repository)
    team_gap_analyzer = TeamGapAnalyzer(
        availability_date_service=availability_date_service
    )
    return AIService(
        system_config_service=system_config_service,
        resource_repository=resource_repository,
        project_repository=ProjectRepository(session),
        candidate_service=SkillMatchCandidateService(
            resource_repository=resource_repository,
            allocation_repository=allocation_repository,
            timesheet_repository=timesheet_repository,
        ),
        project_facts_service=ProjectFactsService(
            project_repository=ProjectRepository(session),
            milestone_repository=MilestoneRepository(session),
            allocation_repository=allocation_repository,
            project_health_service=project_health_service,
        ),
        llm_factory=LLMFactory(),
        team_build_candidate_service=TeamBuildCandidateService(
            resource_repository=resource_repository,
            timesheet_repository=timesheet_repository,
        ),
        team_diagnostics_service=TeamDiagnosticsService(
            resource_repository=resource_repository,
        ),
        team_gap_analyzer=team_gap_analyzer,
    )


dependency_provider.get_ai_service = get_ai_service
