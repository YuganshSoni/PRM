from pydantic import BaseModel


class SkillMatchCandidateResponse(BaseModel):
    resource_id: int
    resource_name: str
    reason: str
    free_hours_per_week: float | None = None
    suggested_utilisation_percent: int | None = None
    rank: int


class SkillMatchResponse(BaseModel):
    items: list[SkillMatchCandidateResponse]
    message: str | None = None
    llm_invoked: bool
    weekly_hours_requested: int | None = None


class RiskSummaryResponse(BaseModel):
    project_id: int
    project_name: str
    summary: str
    disclaimer: str
    llm_invoked: bool
