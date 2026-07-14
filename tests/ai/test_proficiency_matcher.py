from server.ai.dto.team_build import RoleRequirementDTO, SkillProficiencyDTO
from server.ai.services.proficiency_matcher import ProficiencyMatcher
from server.models.enums import ProficiencyLevel, SkillCategoryEnum


def _skill(
    name: str,
    proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE,
    category: SkillCategoryEnum = SkillCategoryEnum.BACKEND,
) -> SkillProficiencyDTO:
    return SkillProficiencyDTO(
        skill_name=name, category=category, proficiency=proficiency
    )


def _role(
    *,
    skill_names: list[str] | None = None,
    skill_category: SkillCategoryEnum | None = None,
    min_proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE,
) -> RoleRequirementDTO:
    return RoleRequirementDTO(
        role_key="r1",
        role_title="Engineer",
        skill_names=skill_names or [],
        skill_category=skill_category,
        min_proficiency=min_proficiency,
    )


def test_meets_role_by_exact_named_skill():
    matcher = ProficiencyMatcher()
    role = _role(skill_names=["Python"])
    skills = [_skill("Python", ProficiencyLevel.INTERMEDIATE)]

    assert matcher.meets_role(role, skills) is True


def test_meets_role_named_skill_is_case_insensitive():
    matcher = ProficiencyMatcher()
    role = _role(skill_names=["python"])
    skills = [_skill("Python", ProficiencyLevel.INTERMEDIATE)]

    assert matcher.meets_role(role, skills) is True


def test_meets_role_rejects_higher_proficiency():
    matcher = ProficiencyMatcher()
    role = _role(
        skill_names=["Python"],
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
    )
    skills = [_skill("Python", ProficiencyLevel.ADVANCED)]

    assert matcher.meets_role(role, skills) is False


def test_meets_role_rejects_lower_proficiency():
    matcher = ProficiencyMatcher()
    role = _role(
        skill_names=["Python"],
        min_proficiency=ProficiencyLevel.ADVANCED,
    )
    skills = [_skill("Python", ProficiencyLevel.INTERMEDIATE)]

    assert matcher.meets_role(role, skills) is False


def test_meets_role_any_of_named_skills():
    matcher = ProficiencyMatcher()
    role = _role(skill_names=["Python", "Go"])
    skills = [_skill("Go", ProficiencyLevel.INTERMEDIATE)]

    assert matcher.meets_role(role, skills) is True


def test_meets_role_by_category_exact_proficiency():
    matcher = ProficiencyMatcher()
    role = _role(
        skill_category=SkillCategoryEnum.QA,
        min_proficiency=ProficiencyLevel.BEGINNER,
    )
    skills = [
        _skill("Selenium", ProficiencyLevel.BEGINNER, SkillCategoryEnum.QA),
    ]

    assert matcher.meets_role(role, skills) is True


def test_meets_role_rejects_category_wrong_proficiency():
    matcher = ProficiencyMatcher()
    role = _role(
        skill_category=SkillCategoryEnum.QA,
        min_proficiency=ProficiencyLevel.BEGINNER,
    )
    skills = [
        _skill("Selenium", ProficiencyLevel.ADVANCED, SkillCategoryEnum.QA),
    ]

    assert matcher.meets_role(role, skills) is False


def test_meets_role_false_without_skills_or_category():
    matcher = ProficiencyMatcher()
    assert matcher.meets_role(_role(), []) is False


def test_named_skills_take_precedence_over_category():
    matcher = ProficiencyMatcher()
    role = _role(
        skill_names=["Python"],
        skill_category=SkillCategoryEnum.QA,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
    )
    # Category match alone would succeed, but named skill is required path.
    skills = [_skill("Selenium", ProficiencyLevel.INTERMEDIATE, SkillCategoryEnum.QA)]

    assert matcher.meets_role(role, skills) is False


def test_score_role_match_returns_none_when_not_met():
    matcher = ProficiencyMatcher()
    role = _role(skill_names=["Python"])
    assert matcher.score_role_match(role, []) is None


def test_score_role_match_base_plus_named_skill_bonus():
    matcher = ProficiencyMatcher()
    role = _role(skill_names=["Python", "SQL"])
    skills = [
        _skill("Python"),
        _skill("SQL"),
        _skill("Docker", ProficiencyLevel.ADVANCED, SkillCategoryEnum.DEVOPS),
    ]

    # base 10 + 5 per matching named skill = 20
    assert matcher.score_role_match(role, skills) == 20


def test_score_role_match_includes_category_bonus():
    matcher = ProficiencyMatcher()
    role = _role(
        skill_names=["Python"],
        skill_category=SkillCategoryEnum.BACKEND,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
    )
    skills = [
        _skill("Python", ProficiencyLevel.INTERMEDIATE, SkillCategoryEnum.BACKEND),
    ]

    # base 10 + named 5 + category 3 = 18
    assert matcher.score_role_match(role, skills) == 18


def test_category_label():
    assert ProficiencyMatcher.category_label(SkillCategoryEnum.FRONTEND) == "FRONTEND"
    assert ProficiencyMatcher.category_label(None) == "ANY"
