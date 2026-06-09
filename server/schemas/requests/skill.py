from pydantic import BaseModel, Field

from server.models.enums import ProficiencyLevel, SkillCategory


class AddSkillRequest(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    category: SkillCategory
    proficiency_level: ProficiencyLevel


class UpdateSkillProficiencyRequest(BaseModel):
    proficiency_level: ProficiencyLevel
