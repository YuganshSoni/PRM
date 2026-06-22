from pydantic import BaseModel, Field


class SkillMatchRequest(BaseModel):
    requirement: str = Field(..., min_length=10, max_length=2000)
    project_id: int | None = None


class TeamBuildRequest(BaseModel):
    requirement: str = Field(..., min_length=10, max_length=2000)
    project_id: int
