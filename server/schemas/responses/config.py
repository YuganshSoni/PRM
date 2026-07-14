from datetime import datetime

from pydantic import BaseModel, ConfigDict

from server.models.enums import LlmProvider
from server.schemas.response_values import ConfigMessage


class SystemConfigResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    llm_provider: LlmProvider
    llm_api_key_masked: str
    scheduler_interval_hours: int
    max_weekly_hours: int
    email_enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password_masked: str
    smtp_from_email: str
    updated_at: datetime


class SystemConfigUpdatedResponse(BaseModel):
    message: ConfigMessage
