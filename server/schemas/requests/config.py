from pydantic import BaseModel, Field

from server.models.enums import LlmProvider


class UpdateSystemConfigRequest(BaseModel):
    llm_api_key: str | None = None
    llm_provider: LlmProvider | None = None
    scheduler_interval_hours: int | None = Field(default=None, ge=1, le=24)
    max_weekly_hours: int | None = Field(default=None, ge=1, le=168)
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    email_enabled: bool | None = None
