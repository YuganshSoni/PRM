from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.ai.services.team_build_candidate_service import TeamBuildCandidateService
from server.models.enums import ProficiencyLevel, SkillCategoryEnum


def _service(*, team=None, timesheet_repo=None):
    return TeamBuildCandidateService(
        manager_team_service=team or AsyncMock(),
        timesheet_repository=timesheet_repo or AsyncMock(),
    )


def _resource(resource_id: int, name: str | None, skills):
    user = None if name is None else SimpleNamespace(full_name=name)
    return SimpleNamespace(id=resource_id, user=user, skills=skills)


@pytest.mark.asyncio
async def test_load_bench_for_manager_maps_skills_and_tags():
    skills = [
        SimpleNamespace(
            proficiency_level="ADVANCED",
            skill=SimpleNamespace(
                name="Python",
                category=SimpleNamespace(name="BACKEND"),
            ),
        ),
        SimpleNamespace(skill=None, proficiency_level="BEGINNER"),
        SimpleNamespace(
            proficiency_level="INTERMEDIATE",
            skill=SimpleNamespace(name="NoCat", category=None),
        ),
    ]
    team = AsyncMock()
    team.list_bench_team_members.return_value = [
        _resource(1, "Ada", skills),
        _resource(2, None, []),
    ]
    timesheet_repo = AsyncMock()
    timesheet_repo.find_recent_activity_tags.side_effect = [["API"], []]

    result = await _service(team=team, timesheet_repo=timesheet_repo).load_bench_for_manager(
        42
    )

    assert len(result) == 2
    assert result[0].resource_name == "Ada"
    assert len(result[0].skills) == 1
    assert result[0].skills[0].skill_name == "Python"
    assert result[0].skills[0].category == SkillCategoryEnum.BACKEND
    assert result[0].skills[0].proficiency == ProficiencyLevel.ADVANCED
    assert result[0].recent_activity_tags == ["API"]
    assert result[1].resource_name == "Resource"
    assert result[1].skills == []
    team.list_bench_team_members.assert_awaited_once_with(42, load_skills=True)


@pytest.mark.asyncio
async def test_load_bench_for_manager_empty_pool():
    team = AsyncMock()
    team.list_bench_team_members.return_value = []

    result = await _service(team=team).load_bench_for_manager(1)

    assert result == []


def test_map_skills_skips_incomplete_entries():
    resource = _resource(
        1,
        "Ada",
        [
            SimpleNamespace(
                proficiency_level="BEGINNER",
                skill=SimpleNamespace(
                    name="React",
                    category=SimpleNamespace(name="FRONTEND"),
                ),
            ),
            SimpleNamespace(skill=None, proficiency_level="BEGINNER"),
        ],
    )
    mapped = TeamBuildCandidateService._map_skills(resource)
    assert len(mapped) == 1
    assert mapped[0].skill_name == "React"
    assert mapped[0].category == SkillCategoryEnum.FRONTEND
