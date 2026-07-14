from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.ai.services.team_diagnostics_service import TeamDiagnosticsService
from server.models.enums import ProficiencyLevel, ResourceStatusEnum, SkillCategoryEnum


def _service(*, team=None):
    return TeamDiagnosticsService(manager_team_service=team or AsyncMock())


def _resource(resource_id: int, name: str | None, status_name: str | None, skills):
    user = None if name is None else SimpleNamespace(full_name=name)
    status = None if status_name is None else SimpleNamespace(name=status_name)
    return SimpleNamespace(
        id=resource_id,
        user=user,
        resource_status=status,
        skills=skills,
    )


@pytest.mark.asyncio
async def test_load_for_manager_marks_bench_and_maps_skills():
    skills = [
        SimpleNamespace(
            proficiency_level="INTERMEDIATE",
            skill=SimpleNamespace(
                name="Go",
                category=SimpleNamespace(name="BACKEND"),
            ),
        ),
        SimpleNamespace(skill=None, proficiency_level="BEGINNER"),
    ]
    team = AsyncMock()
    team.list_active_team_members.return_value = [
        _resource(1, "Ada", ResourceStatusEnum.BENCH.value, skills),
        _resource(2, None, None, []),
        _resource(3, "Bob", ResourceStatusEnum.ALLOCATED.value, []),
    ]

    result = await _service(team=team).load_for_manager(99)

    assert len(result) == 3
    assert result[0].is_bench is True
    assert result[0].resource_name == "Ada"
    assert result[0].skills[0].skill_name == "Go"
    assert result[0].skills[0].proficiency == ProficiencyLevel.INTERMEDIATE
    assert result[0].skills[0].category == SkillCategoryEnum.BACKEND
    assert result[1].resource_name == "Resource"
    assert result[1].is_bench is False
    assert result[2].is_bench is False
    team.list_active_team_members.assert_awaited_once_with(99, load_skills=True)


@pytest.mark.asyncio
async def test_load_for_manager_empty():
    team = AsyncMock()
    team.list_active_team_members.return_value = []
    assert await _service(team=team).load_for_manager(1) == []


def test_map_skills_helper():
    resource = _resource(
        1,
        "Ada",
        "BENCH",
        [
            SimpleNamespace(
                proficiency_level="ADVANCED",
                skill=SimpleNamespace(
                    name="Docker",
                    category=SimpleNamespace(name="DEVOPS"),
                ),
            )
        ],
    )
    mapped = TeamDiagnosticsService._map_skills(resource)
    assert len(mapped) == 1
    assert mapped[0].category == SkillCategoryEnum.DEVOPS
