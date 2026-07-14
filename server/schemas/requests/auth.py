from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        return value.strip()


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=1)
    confirm_password: str = Field(min_length=1)
