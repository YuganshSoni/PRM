from pydantic import BaseModel, ConfigDict

from server.models.enums import UserRole, UserStatus


class UserSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    username: str
    full_name: str
    role: UserRole
    status: UserStatus


class UserCreatedResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    username: str
    role: UserRole
    message: str


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
    message: str
