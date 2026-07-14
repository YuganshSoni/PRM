from pydantic import BaseModel, ConfigDict

from server.models.enums import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    access_token: str
    token_type: str
    role: UserRole
    force_password_change: bool
    full_name: str


class ChangePasswordResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    access_token: str
    token_type: str
    role: UserRole
    force_password_change: bool
    message: str


class LogoutResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    message: str


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    username: str
    role: UserRole
    force_password_change: bool


class ErrorBody(BaseModel):
    detail: str
    code: str
