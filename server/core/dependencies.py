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
from server.repositories.user_repository import UserRepository
from server.services.auth_service import AuthService


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
