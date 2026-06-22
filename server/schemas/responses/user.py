from pydantic import BaseModel, ConfigDict

from server.models.enums import UserRole, UserStatus
from server.schemas.response_values import UserMessage


class UserSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    username: str
    full_name: str
    role: UserRole
    status: UserStatus


class UserResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    force_password_change: bool


class UserCreatedResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    username: str
    role: UserRole
    message: UserMessage


class UserListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    items: list[UserSummaryResponse]
    total: int
    active_count: int
    inactive_count: int
    limit: int
    offset: int


class UserActionResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    user_id: int
    message: UserMessage
