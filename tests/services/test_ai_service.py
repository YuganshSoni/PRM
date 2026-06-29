from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.ai.chains.parse_skill_match_requirement_chain import (
    ParsedSkillMatchRequirementOutput,
)
from server.core.exceptions import (
    InvalidSkillMatchRequestError,
    InvalidTeamBuildRequestError,
    LlmInvocationError,
    ProjectNotFoundError,
)
from server.models.enums import LlmProvider, ProficiencyLevel
from server.schemas.requests.ai import SkillMatchRequest, TeamBuildRequest
from server.services.ai_service import AIService, TEAM_BUILD_DISCLAIMER, RISK_SUMMARY_DISCLAIMER


def _llm_config():
    return SimpleNamespace(
        provider=LlmProvider.GEMINI,
        api_key="test-key",
        max_weekly_hours=40,
    )


def _user():
    user = MagicMock()
    user.id = 1
    return user


def _service(**overrides) -> AIService:
    defaults = dict(
        system_config_service=AsyncMock(),
        resource_repository=AsyncMock(),
        project_repository=AsyncMock(),
        candidate_service=AsyncMock(),
        project_facts_service=AsyncMock(),
        llm_factory=MagicMock(),
        team_build_candidate_service=AsyncMock(),
        team_diagnostics_service=AsyncMock(),
        team_gap_analyzer=MagicMock(),
        manager_team_service=AsyncMock(),
        skill_match_runner=MagicMock(),
        risk_summary_runner=MagicMock(),
        team_build_runner=AsyncMock(),
    )
    defaults.update(overrides)
    defaults["system_config_service"].get_llm_config.return_value = _llm_config()
    defaults["manager_team_service"].resolve_manager_resource_id.return_value = 100
    defaults["llm_factory"].create.return_value = MagicMock()
    return AIService(**defaults)


@pytest.mark.asyncio
async def test_skill_match_rejects_short_requirement():
    # pydantic min_length=10 blocks empty DTO; bypass via MagicMock
    request = MagicMock()
    request.requirement = "short"
    request.project_id = None
    with pytest.raises(InvalidSkillMatchRequestError):
        await _service().skill_match(_user(), request)


@pytest.mark.asyncio
async def test_skill_match_ensures_project_owned():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = None
    service = _service(project_repository=project_repo)
    request = SkillMatchRequest(
        requirement="Need a senior React developer for 20h",
        project_id=9,
    )
    with pytest.raises(ProjectNotFoundError):
        await service.skill_match(_user(), request)


@pytest.mark.asyncio
async def test_skill_match_vague_requirement_early_exit():
    service = _service()
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=None,
        skill_names=[],
        role_title=None,
        skill_category=None,
        seniority=None,
        summary="Vague staffing ask",
    )
    with patch(
        "server.services.ai_service.ParseSkillMatchRequirementChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = parsed
        result = await service.skill_match(
            _user(),
            SkillMatchRequest(requirement="Need someone to help shortly"),
        )

    assert result.items == []
    assert "Could not identify" in result.message
    assert result.llm_invoked is False
    assert result.requirement_parse_invoked is True


@pytest.mark.asyncio
async def test_skill_match_no_candidates_early_exit():
    candidate_service = AsyncMock()
    candidate_service.load_for_manager.return_value = []
    service = _service(candidate_service=candidate_service)
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=20,
        skill_names=["React"],
        role_title="Developer",
        skill_category=None,
        seniority=None,
        summary="React developer 20h",
    )
    with patch(
        "server.services.ai_service.ParseSkillMatchRequirementChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = parsed
        result = await service.skill_match(
            _user(),
            SkillMatchRequest(requirement="Need a React developer for 20 hours"),
        )

    assert result.items == []
    assert "No employees" in result.message
    assert result.weekly_hours_requested == 20


@pytest.mark.asyncio
async def test_skill_match_ranks_candidates():
    candidate_service = AsyncMock()
    candidate_service.load_for_manager.return_value = [{"resource_id": 1}]
    runner = MagicMock()
    runner.invoke.return_value = {
        "ranked_items": [
            {
                "resource_id": 1,
                "resource_name": "Ada",
                "reason": "Strong React",
                "free_hours_per_week": 20,
                "suggested_utilisation_percent": 50,
                "rank": 1,
            }
        ],
        "llm_invoked": True,
        "message": None,
        "weekly_hours": 20,
    }
    service = _service(
        candidate_service=candidate_service,
        skill_match_runner=runner,
    )
    parsed = ParsedSkillMatchRequirementOutput(
        weekly_hours=20,
        skill_names=["React"],
        role_title="Developer",
        skill_category=None,
        seniority=None,
        summary="React developer",
    )
    with patch(
        "server.services.ai_service.ParseSkillMatchRequirementChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = parsed
        result = await service.skill_match(
            _user(),
            SkillMatchRequest(requirement="Need a React developer for 20 hours"),
        )

    assert len(result.items) == 1
    assert result.items[0].resource_name == "Ada"
    assert result.llm_invoked is True


@pytest.mark.asyncio
async def test_skill_match_parse_failure_maps_llm_error():
    service = _service()
    with patch(
        "server.services.ai_service.ParseSkillMatchRequirementChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.side_effect = RuntimeError("llm down")
        with pytest.raises(LlmInvocationError):
            await service.skill_match(
                _user(),
                SkillMatchRequest(requirement="Need a React developer for 20 hours"),
            )


@pytest.mark.asyncio
async def test_team_build_rejects_short_requirement():
    request = MagicMock()
    request.requirement = "too short"
    request.project_id = 1
    with pytest.raises(InvalidTeamBuildRequestError):
        await _service().team_build(_user(), request)


@pytest.mark.asyncio
async def test_team_build_happy_path():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = SimpleNamespace(
        id=5, manager_id=100
    )
    role = SimpleNamespace(
        role_key="r1",
        role_title="Backend",
        skill_names=["Python"],
        skill_category=None,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
    )
    assignment = SimpleNamespace(
        role_key="r1",
        role_title="Backend",
        resource_id=1,
        resource_name="Ada",
        reason="fit",
        match_score=90,
    )
    gap = SimpleNamespace(
        role_key="r2",
        role_title="QA",
        gap_type=SimpleNamespace(value="NO_CANDIDATE"),
        message="missing",
        available_from=None,
        candidate_hint_name=None,
    )
    runner = AsyncMock()
    runner.invoke.return_value = {
        "parsed_roles": [role],
        "assignments": [assignment],
        "gaps": [gap],
        "llm_invoked": True,
    }
    service = _service(project_repository=project_repo, team_build_runner=runner)

    result = await service.team_build(
        _user(),
        TeamBuildRequest(
            requirement="Build a backend and QA team for launch",
            project_id=5,
        ),
    )

    assert result.project_id == 5
    assert len(result.parsed_roles) == 1
    assert len(result.matches) == 1
    assert len(result.gaps) == 1
    assert result.disclaimer == TEAM_BUILD_DISCLAIMER
    assert result.llm_invoked is True


@pytest.mark.asyncio
async def test_risk_summary_happy_path():
    facts = MagicMock()
    facts.project_name = "Apollo"
    facts.to_prompt_text.return_value = "facts"
    facts_service = AsyncMock()
    facts_service.collect.return_value = facts
    runner = MagicMock()
    runner.invoke.return_value = {
        "summary": "Elevated risk",
        "llm_invoked": True,
    }
    service = _service(
        project_facts_service=facts_service,
        risk_summary_runner=runner,
    )

    result = await service.risk_summary(_user(), 5)

    assert result.project_id == 5
    assert result.project_name == "Apollo"
    assert result.summary == "Elevated risk"
    assert result.disclaimer == RISK_SUMMARY_DISCLAIMER
    assert result.llm_invoked is True
