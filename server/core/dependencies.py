from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.core.database import get_db
from server.core.exceptions import ForbiddenError, InvalidTokenError, UserNotFoundError
from server.core.jwt_token_service import JwtTokenService
from server.core.password_policy import PasswordPolicy
from server.core.security import PasswordHasher
from server.models.enums import UserRole
from server.models.user import User
from server.core.api_key_masker import ApiKeyMasker
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.employee_repository import EmployeeRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_repository import ProjectRepository
from server.repositories.skill_repository import SkillRepository
from server.repositories.system_config_repository import SystemConfigRepository
from server.repositories.timesheet_repository import TimesheetRepository
from server.repositories.user_repository import UserRepository
from server.services.allocation_view_service import AllocationViewService
from server.services.auth_service import AuthService
from server.services.employee_service import EmployeeService
from server.services.milestone_service import MilestoneService
from server.services.project_service import ProjectService
from server.services.skill_service import SkillService
from server.services.resource_dashboard_service import ResourceDashboardService
from server.services.system_config_service import SystemConfigService
from server.services.user_service import UserService


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
            if user.role not in allowed:
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
    user_repository: Annotated[
        UserRepository, Depends(dependency_provider.get_user_repository)
    ],
    auth_service: Annotated[AuthService, Depends(dependency_provider.get_auth_service)],
) -> UserService:
    return UserService(
        user_repository=user_repository,
        password_hasher=PasswordHasher(),
        auth_service=auth_service,
    )


dependency_provider.get_user_service = get_user_service


async def get_employee_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_repository: Annotated[
        UserRepository, Depends(dependency_provider.get_user_repository)
    ],
) -> EmployeeService:
    return EmployeeService(
        employee_repository=EmployeeRepository(session),
        user_repository=user_repository,
        allocation_repository=AllocationRepository(session),
    )


dependency_provider.get_employee_service = get_employee_service


async def get_skill_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SkillService:
    return SkillService(
        skill_repository=SkillRepository(session),
        employee_repository=EmployeeRepository(session),
    )


dependency_provider.get_skill_service = get_skill_service


async def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectService:
    return ProjectService(
        project_repository=ProjectRepository(session),
        employee_repository=EmployeeRepository(session),
        milestone_repository=MilestoneRepository(session),
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
        employee_repository=EmployeeRepository(session),
        allocation_repository=AllocationRepository(session),
        skill_repository=SkillRepository(session),
        timesheet_repository=TimesheetRepository(session),
    )


dependency_provider.get_resource_dashboard_service = get_resource_dashboard_service
