from pydantic import BaseModel, Field

from server.models.enums import LlmProvider


class UpdateSystemConfigRequest(BaseModel):
    llm_api_key: str | None = None
    llm_provider: LlmProvider | None = None
    scheduler_interval_hours: int | None = Field(default=None, ge=1, le=24)
    max_weekly_hours: int | None = Field(default=None, ge=1, le=168)
