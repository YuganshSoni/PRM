from server.ai.chains.parse_skill_match_requirement_chain import (
    ParsedSkillMatchRequirementOutput,
)
from server.ai.services.skill_match_requirement_evaluator import (
    SkillMatchRequirementEvaluator,
)
from server.models.enums import SkillCategoryEnum

MAX_WEEKLY_HOURS = 40


def _evaluate(parsed: ParsedSkillMatchRequirementOutput):
    return SkillMatchRequirementEvaluator().evaluate(
        parsed, max_weekly_hours=MAX_WEEKLY_HOURS
    )


def test_vague_query_is_not_actionable():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=None,
        skill_names=[],
        role_title=None,
        skill_category=None,
        seniority=None,
        summary="Generic staffing request",
    )
    result = _evaluate(parsed)
    assert result.is_actionable is False


def test_hours_only_is_actionable():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=20,
        skill_names=[],
        role_title=None,
        skill_category=None,
        seniority=None,
        summary="20 hours per week",
    )
    result = _evaluate(parsed)
    assert result.is_actionable is True
    assert result.weekly_hours == 20


def test_generic_developer_role_is_not_actionable():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=None,
        skill_names=[],
        role_title="developer",
        skill_category=None,
        seniority=None,
        summary="Need a developer",
    )
    result = _evaluate(parsed)
    assert result.is_actionable is False


def test_named_skill_is_actionable():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=None,
        skill_names=["React"],
        role_title="Developer",
        skill_category=None,
        seniority=None,
        summary="React developer",
    )
    result = _evaluate(parsed)
    assert result.is_actionable is True
    assert result.skill_names == ["React"]


def test_skill_category_is_actionable():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=None,
        skill_names=[],
        role_title=None,
        skill_category=SkillCategoryEnum.QA,
        seniority=None,
        summary="QA support",
    )
    result = _evaluate(parsed)
    assert result.is_actionable is True
    assert result.skill_category == SkillCategoryEnum.QA


def test_concrete_role_title_is_actionable():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=None,
        skill_names=[],
        role_title="Senior React Developer",
        skill_category=None,
        seniority="SENIOR",
        summary="Senior React developer",
    )
    result = _evaluate(parsed)
    assert result.is_actionable is True


def test_invalid_weekly_hours_are_discarded():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=500,
        skill_names=[],
        role_title=None,
        skill_category=None,
        seniority=None,
        summary="Unrealistic hours",
    )
    result = _evaluate(parsed)
    assert result.weekly_hours is None
    assert result.is_actionable is False


def test_duplicate_skills_are_deduplicated():
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=None,
        skill_names=["React", "react", " Java "],
        role_title=None,
        skill_category=None,
        seniority=None,
        summary="React and Java",
    )
    result = _evaluate(parsed)
    assert result.skill_names == ["React", "Java"]
