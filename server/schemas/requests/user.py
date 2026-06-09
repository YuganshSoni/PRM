from pydantic import BaseModel, EmailStr, Field

from server.models.enums import UserRole


class CreateUserRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=64)
    temporary_password: str = Field(..., min_length=1)
    role: UserRole


class ResetPasswordRequest(BaseModel):
    temporary_password: str = Field(..., min_length=1)
