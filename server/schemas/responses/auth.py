from pydantic import BaseModel, ConfigDict

from server.models.enums import UserRole
from server.schemas.response_values import AuthMessage, TokenType


class LoginResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    access_token: str
    token_type: TokenType
    role: UserRole
    force_password_change: bool
    full_name: str


class ChangePasswordResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    access_token: str
    token_type: TokenType
    role: UserRole
    force_password_change: bool
    message: AuthMessage


class LogoutResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    message: AuthMessage


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    username: str
    role: UserRole
    force_password_change: bool
