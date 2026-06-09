from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from server.core.dependencies import dependency_provider
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.requests.user import CreateUserRequest, ResetPasswordRequest
from server.schemas.response_values import UserMessage
from server.schemas.responses.user import (
    UserActionResponse,
    UserCreatedResponse,
    UserListResponse,
    UserResponse,
    UserSummaryResponse,
)
from server.services.user_service import UserService


class UserRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/users", tags=["users"])
        self.router.add_api_route(
            "",
            self.create_user,
            methods=["POST"],
            response_model=UserCreatedResponse,
            status_code=status.HTTP_201_CREATED,
        )
        self.router.add_api_route(
            "",
            self.list_users,
            methods=["GET"],
            response_model=UserListResponse,
        )
        self.router.add_api_route(
            "/lookup",
            self.lookup_user,
            methods=["GET"],
            response_model=UserSummaryResponse,
        )
        self.router.add_api_route(
            "/{user_id}",
            self.get_user,
            methods=["GET"],
            response_model=UserResponse,
        )
        self.router.add_api_route(
            "/{user_id}/reset-password",
            self.reset_password,
            methods=["POST"],
            response_model=UserActionResponse,
        )
        self.router.add_api_route(
            "/{user_id}/deactivate",
            self.deactivate_user,
            methods=["POST"],
            response_model=UserActionResponse,
        )
        self.router.add_api_route(
            "/{user_id}/reactivate",
            self.reactivate_user,
            methods=["POST"],
            response_model=UserActionResponse,
        )

    async def create_user(
        self,
        body: CreateUserRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        user_service: UserService = Depends(dependency_provider.get_user_service),
    ) -> UserCreatedResponse:
        user = await user_service.create_user(body)
        return UserCreatedResponse(
            id=user.id,
            username=user.username,
            role=UserRole(user.role),
            message=UserMessage.ACCOUNT_CREATED,
        )

    async def list_users(
        self,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        user_service: UserService = Depends(dependency_provider.get_user_service),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> UserListResponse:
        result = await user_service.list_users(limit, offset)
        return UserListResponse(
            items=[self._to_summary(user) for user in result.items],
            total=result.total,
            active_count=result.active_count,
            inactive_count=result.inactive_count,
            limit=limit,
            offset=offset,
        )

    async def lookup_user(
        self,
        identifier: Annotated[str, Query(min_length=1)],
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        user_service: UserService = Depends(dependency_provider.get_user_service),
    ) -> UserSummaryResponse:
        user = await user_service.lookup_user(identifier)
        return self._to_summary(user)

    async def get_user(
        self,
        user_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        user_service: UserService = Depends(dependency_provider.get_user_service),
    ) -> UserResponse:
        user = await user_service.get_user(user_id)
        return self._to_response(user)

    async def reset_password(
        self,
        user_id: int,
        body: ResetPasswordRequest,
        admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        user_service: UserService = Depends(dependency_provider.get_user_service),
    ) -> UserActionResponse:
        await user_service.reset_password(
            user_id, body.temporary_password, admin.id
        )
        return UserActionResponse(
            user_id=user_id,
            message=UserMessage.PASSWORD_RESET,
        )

    async def deactivate_user(
        self,
        user_id: int,
        admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        user_service: UserService = Depends(dependency_provider.get_user_service),
    ) -> UserActionResponse:
        await user_service.deactivate(user_id, admin.id)
        return UserActionResponse(
            user_id=user_id,
            message=UserMessage.USER_DEACTIVATED,
        )

    async def reactivate_user(
        self,
        user_id: int,
        admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        user_service: UserService = Depends(dependency_provider.get_user_service),
    ) -> UserActionResponse:
        await user_service.reactivate(user_id, admin.id)
        return UserActionResponse(
            user_id=user_id,
            message=UserMessage.USER_REACTIVATED,
        )

    def _to_summary(self, user: User) -> UserSummaryResponse:
        return UserSummaryResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=UserRole(user.role),
            status=user.status,
        )

    def _to_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=UserRole(user.role),
            status=user.status,
            force_password_change=user.force_password_change,
        )
