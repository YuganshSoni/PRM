from unittest.mock import AsyncMock, MagicMock

import pytest

from server.ai.dto.team_build import SkillProficiencyDTO, TeamBuildCandidateDTO
from server.models.enums import ProficiencyLevel, SkillCategoryEnum
from server.notifications.services.at_risk_help_suggestion_service import (
    AtRiskHelpSuggestionService,
)


def _candidate(
    name: str,
    skills: list[SkillProficiencyDTO] | None = None,
) -> TeamBuildCandidateDTO:
    return TeamBuildCandidateDTO(
        resource_id=1,
        resource_name=name,
        skills=skills or [],
        recent_activity_tags=[],
    )


@pytest.mark.asyncio
async def test_suggest_returns_message_when_project_missing():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = None
    bench = AsyncMock()
    service = AtRiskHelpSuggestionService(project_repo, bench)

    result = await service.suggest(99)

    assert result == "No bench suggestions available."
    bench.load_bench_for_manager.assert_not_awaited()


@pytest.mark.asyncio
async def test_suggest_returns_message_when_manager_missing():
    project = MagicMock()
    project.manager_id = None
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = project
    bench = AsyncMock()
    service = AtRiskHelpSuggestionService(project_repo, bench)

    result = await service.suggest(1)

    assert result == "No bench suggestions available."
    bench.load_bench_for_manager.assert_not_awaited()


@pytest.mark.asyncio
async def test_suggest_returns_message_when_no_candidates():
    project = MagicMock()
    project.manager_id = 10
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = project
    bench = AsyncMock()
    bench.load_bench_for_manager.return_value = []
    service = AtRiskHelpSuggestionService(project_repo, bench)

    result = await service.suggest(1)

    assert result == "No bench employees available on the manager's team."
    bench.load_bench_for_manager.assert_awaited_once_with(10)


@pytest.mark.asyncio
async def test_suggest_formats_candidates_with_skills():
    project = MagicMock()
    project.manager_id = 10
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = project
    bench = AsyncMock()
    bench.load_bench_for_manager.return_value = [
        _candidate(
            "Ada",
            [
                SkillProficiencyDTO(
                    skill_name="Python",
                    category=SkillCategoryEnum.BACKEND,
                    proficiency=ProficiencyLevel.ADVANCED,
                ),
                SkillProficiencyDTO(
                    skill_name="SQL",
                    category=SkillCategoryEnum.BACKEND,
                    proficiency=ProficiencyLevel.INTERMEDIATE,
                ),
            ],
        ),
        _candidate("Grace"),
    ]
    service = AtRiskHelpSuggestionService(project_repo, bench)

    result = await service.suggest(1)

    assert result == (
        "- Ada: Python (ADVANCED), SQL (INTERMEDIATE)\n"
        "- Grace: no skills listed"
    )


@pytest.mark.asyncio
async def test_suggest_respects_limit():
    project = MagicMock()
    project.manager_id = 10
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = project
    bench = AsyncMock()
    bench.load_bench_for_manager.return_value = [
        _candidate("A"),
        _candidate("B"),
        _candidate("C"),
    ]
    service = AtRiskHelpSuggestionService(project_repo, bench)

    result = await service.suggest(1, limit=2)

    assert result == "- A: no skills listed\n- B: no skills listed"
    assert "C" not in result
