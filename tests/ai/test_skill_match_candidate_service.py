from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.ai.services.skill_match_candidate_service import SkillMatchCandidateService


def _service(*, team=None, allocation_repo=None, timesheet_repo=None):
    return SkillMatchCandidateService(
        manager_team_service=team or AsyncMock(),
        allocation_repository=allocation_repo or AsyncMock(),
        timesheet_repository=timesheet_repo or AsyncMock(),
    )


def _resource(resource_id: int, name: str | None, skills: list[str]):
    user = None if name is None else SimpleNamespace(full_name=name)
    resource_skills = []
    for skill_name in skills:
        resource_skills.append(
            SimpleNamespace(skill=SimpleNamespace(name=skill_name))
        )
    resource_skills.append(SimpleNamespace(skill=None))
    return SimpleNamespace(id=resource_id, user=user, skills=resource_skills)


@pytest.mark.asyncio
async def test_load_for_manager_returns_empty_when_no_team():
    team = AsyncMock()
    team.list_active_team_members.return_value = []
    allocation_repo = AsyncMock()

    result = await _service(team=team, allocation_repo=allocation_repo).load_for_manager(
        10, max_weekly_hours=40
    )

    assert result == []
    allocation_repo.find_active_by_team.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_for_manager_builds_candidates_with_utilisation():
    team = AsyncMock()
    team.list_active_team_members.return_value = [
        _resource(1, "Ada", ["Python"]),
        _resource(2, None, ["Go"]),
    ]
    allocation_repo = AsyncMock()
    allocation_repo.find_active_by_team.return_value = [
        SimpleNamespace(resource_id=1, utilisation_percent=25),
        SimpleNamespace(resource_id=1, utilisation_percent=25),
        SimpleNamespace(resource_id=2, utilisation_percent=10),
    ]
    timesheet_repo = AsyncMock()
    timesheet_repo.find_recent_activity_tags.side_effect = [
        ["Backend"],
        ["Frontend"],
    ]

    result = await _service(
        team=team,
        allocation_repo=allocation_repo,
        timesheet_repo=timesheet_repo,
    ).load_for_manager(7, max_weekly_hours=40)

    assert len(result) == 2
    assert result[0].resource_id == 1
    assert result[0].resource_name == "Ada"
    assert result[0].utilisation_percent == 50
    assert result[0].free_hours_per_week == 20.0
    assert result[0].skills == ["Python"]
    assert result[0].recent_activity_tags == ["Backend"]
    assert result[1].resource_name == "Resource"
    assert result[1].utilisation_percent == 10
    assert result[1].free_hours_per_week == 36.0
    team.list_active_team_members.assert_awaited_once_with(7, load_skills=True)
    allocation_repo.find_active_by_team.assert_awaited_once_with(7)


def test_sum_utilisation_aggregates_by_resource():
    totals = SkillMatchCandidateService._sum_utilisation(
        [
            SimpleNamespace(resource_id=1, utilisation_percent=40),
            SimpleNamespace(resource_id=2, utilisation_percent=10),
            SimpleNamespace(resource_id=1, utilisation_percent=5),
        ]
    )
    assert totals == {1: 45, 2: 10}


def test_sum_utilisation_empty():
    assert SkillMatchCandidateService._sum_utilisation([]) == {}
