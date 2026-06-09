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
    updated_at: datetime


class SystemConfigUpdatedResponse(BaseModel):
    message: ConfigMessage
