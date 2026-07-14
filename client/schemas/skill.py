from pydantic import BaseModel, ConfigDict

from server.models.enums import ProficiencyLevel, SkillCategoryEnum


class SkillResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    skill_name: str
    category: SkillCategoryEnum
    proficiency_level: ProficiencyLevel


class SkillListResponse(BaseModel):
    items: list[SkillResponse]
