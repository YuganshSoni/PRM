from server.ai.dto.team_build import RoleRequirementDTO, SkillProficiencyDTO
from server.models.enums import ProficiencyLevel, SkillCategoryEnum


class ProficiencyMatcher:
    """Exact proficiency matching — higher levels do not satisfy lower requirements."""

    def meets_role(
        self, role: RoleRequirementDTO, skills: list[SkillProficiencyDTO]
    ) -> bool:
        if role.skill_names:
            return any(
                self._matches_named_skill(name, role.min_proficiency, skills)
                for name in role.skill_names
            )
        if role.skill_category is not None:
            return any(
                skill.category == role.skill_category
                and skill.proficiency == role.min_proficiency
                for skill in skills
            )
        return False

    def score_role_match(
        self, role: RoleRequirementDTO, skills: list[SkillProficiencyDTO]
    ) -> int | None:
        if not self.meets_role(role, skills):
            return None

        score = 10
        normalized_names = {name.lower() for name in role.skill_names}
        for skill in skills:
            if skill.skill_name.lower() in normalized_names:
                score += 5
            if (
                role.skill_category is not None
                and skill.category == role.skill_category
                and skill.proficiency == role.min_proficiency
            ):
                score += 3
        return score

    @staticmethod
    def _matches_named_skill(
        skill_name: str,
        required: ProficiencyLevel,
        skills: list[SkillProficiencyDTO],
    ) -> bool:
        target = skill_name.lower()
        return any(
            skill.skill_name.lower() == target and skill.proficiency == required
            for skill in skills
        )

    @staticmethod
    def category_label(category: SkillCategoryEnum | None) -> str:
        return category.value if category is not None else "ANY"
