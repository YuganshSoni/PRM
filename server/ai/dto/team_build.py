from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from server.models.enums import ProficiencyLevel, SkillCategoryEnum


class TeamGapType(StrEnum):
    SKILL_ABSENCE = "SKILL_ABSENCE"
    AVAILABILITY_CONFLICT = "AVAILABILITY_CONFLICT"


@dataclass(frozen=True)
class SkillProficiencyDTO:
    skill_name: str
    category: SkillCategoryEnum
    proficiency: ProficiencyLevel


@dataclass(frozen=True)
class RoleRequirementDTO:
    role_key: str
    role_title: str
    skill_names: list[str]
    skill_category: SkillCategoryEnum | None
    min_proficiency: ProficiencyLevel


@dataclass(frozen=True)
class TeamBuildCandidateDTO:
    resource_id: int
    resource_name: str
    skills: list[SkillProficiencyDTO]
    recent_activity_tags: list[str]

    def to_prompt_line(self) -> str:
        skills_text = ", ".join(
            f"{skill.skill_name} ({skill.proficiency.value}, {skill.category.value})"
            for skill in self.skills
        ) or "none listed"
        tags_text = (
            ", ".join(self.recent_activity_tags)
            if self.recent_activity_tags
            else "none"
        )
        return (
            f"Name: {self.resource_name}; "
            f"Skills: {skills_text}; "
            f"Recent activity tags: {tags_text}"
        )


@dataclass(frozen=True)
class TeamDiagnosticMemberDTO:
    resource_id: int
    resource_name: str
    is_bench: bool
    skills: list[SkillProficiencyDTO]


@dataclass(frozen=True)
class RoleAssignmentDTO:
    role_key: str
    role_title: str
    resource_id: int
    resource_name: str
    match_score: int
    reason: str = ""


@dataclass(frozen=True)
class RoleGapDTO:
    role_key: str
    role_title: str
    gap_type: TeamGapType
    message: str
    available_from: date | None = None
    candidate_hint_name: str | None = None
