from fastapi import APIRouter, Depends

from server.core.dependencies import dependency_provider
from server.core.user_role import user_role_enum
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.requests.auth import ChangePasswordRequest, LoginRequest
from server.schemas.response_values import AuthMessage, TokenType
from server.schemas.responses.auth import (
    ChangePasswordResponse,
    CurrentUserResponse,
    LoginResponse,
    LogoutResponse,
)
from server.services.auth_service import AuthService


class AuthRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/auth", tags=["auth"])
        self.router.add_api_route(
            "/login",
            self.login,
            methods=["POST"],
            response_model=LoginResponse,
        )
        self.router.add_api_route(
            "/change-password",
            self.change_password,
            methods=["POST"],
            response_model=ChangePasswordResponse,
        )
        self.router.add_api_route(
            "/logout",
            self.logout,
            methods=["POST"],
            response_model=LogoutResponse,
        )
        self.router.add_api_route(
            "/me",
            self.me,
            methods=["GET"],
            response_model=CurrentUserResponse,
        )

    async def login(
        self,
        body: LoginRequest,
        auth_service: AuthService = Depends(dependency_provider.get_auth_service),
    ) -> LoginResponse:
        result = await auth_service.login(body.username, body.password)
        return LoginResponse(
            access_token=result.access_token,
            token_type=TokenType.BEARER,
            role=user_role_enum(result.user),
            force_password_change=result.user.force_password_change,
            full_name=result.user.full_name,
        )

    async def change_password(
        self,
        body: ChangePasswordRequest,
        user: User = Depends(dependency_provider.get_current_user),
        auth_service: AuthService = Depends(dependency_provider.get_auth_service),
    ) -> ChangePasswordResponse:
        result = await auth_service.change_password(
            user, body.new_password, body.confirm_password
        )
        return ChangePasswordResponse(
            access_token=result.access_token,
            token_type=TokenType.BEARER,
            role=user_role_enum(result.user),
            force_password_change=result.user.force_password_change,
            message=AuthMessage.PASSWORD_UPDATED,
        )

    async def logout(
        self,
        _user: User = Depends(dependency_provider.get_current_user),
    ) -> LogoutResponse:
        return LogoutResponse(message=AuthMessage.LOGOUT_SUCCESS)

    async def me(
        self,
        user: User = Depends(dependency_provider.get_current_user),
    ) -> CurrentUserResponse:
        return CurrentUserResponse(
            id=user.id,
            username=user.username,
            role=user_role_enum(user),
            force_password_change=user.force_password_change,
        )
