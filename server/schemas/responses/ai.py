from datetime import date

from pydantic import BaseModel, Field, model_validator

from server.models.enums import ProficiencyLevel, SkillCategoryEnum


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


class ParsedTeamRoleResponse(BaseModel):
    role_key: str
    role_title: str
    skill_names: list[str]
    skill_category: SkillCategoryEnum | None = None
    min_proficiency: ProficiencyLevel


class TeamRoleMatchResponse(BaseModel):
    role_key: str
    role_title: str
    resource_id: int
    resource_name: str
    reason: str
    match_score: int


class TeamRoleGapResponse(BaseModel):
    role_key: str
    role_title: str
    gap_type: str
    message: str
    available_from: date | None = None
    candidate_hint_name: str | None = None


class TeamBuildResponse(BaseModel):
    project_id: int
    parsed_roles: list[ParsedTeamRoleResponse]
    matches: list[TeamRoleMatchResponse]
    gaps: list[TeamRoleGapResponse]
    llm_invoked: bool
    disclaimer: str = (
        "AI-generated team suggestions — verify before allocating."
    )


class RiskSummaryResponse(BaseModel):
    project_id: int
    project_name: str
    summary: str
    disclaimer: str = (
        "This summary is AI-generated from milestone and timesheet data."
    )
    llm_invoked: bool
