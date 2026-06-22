from datetime import date

from pydantic import BaseModel


class ParsedTeamRoleResponse(BaseModel):
    role_key: str
    role_title: str
    skill_names: list[str]
    skill_category: str | None = None
    min_proficiency: str


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
    disclaimer: str
