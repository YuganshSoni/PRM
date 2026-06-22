from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SystemConfigResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    llm_provider: str
    llm_api_key_masked: str
    scheduler_interval_hours: int
    max_weekly_hours: int
    updated_at: datetime


class SystemConfigUpdatedResponse(BaseModel):
    message: str
