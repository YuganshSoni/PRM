from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.ai.chains.parse_team_requirement_chain import (
    ParsedRoleItem,
    ParseTeamRequirementChainOutput,
)
from server.ai.chains.team_match_reason_chain import (
    RoleReasonItem,
    TeamMatchReasonChainOutput,
)
from server.ai.dto.team_build import (
    RoleAssignmentDTO,
    RoleGapDTO,
    RoleRequirementDTO,
    TeamGapType,
)
from server.ai.nodes.team_build_nodes import (
    AnalyzeTeamGapsNode,
    FormatTeamBuildResultsNode,
    InvokeTeamMatchReasonNode,
    ParseTeamRequirementNode,
    SolveTeamAssignmentNode,
)
from server.core.exceptions import InvalidTeamBuildRequestError, LlmInvocationError
from server.models.enums import ProficiencyLevel


def _role(key: str = "role_1") -> RoleRequirementDTO:
    return RoleRequirementDTO(
        role_key=key,
        role_title="Backend",
        skill_names=["Python"],
        skill_category=None,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
    )


def _assignment(key: str = "role_1") -> RoleAssignmentDTO:
    return RoleAssignmentDTO(
        role_key=key,
        role_title="Backend",
        resource_id=1,
        resource_name="Ada",
        match_score=90,
        reason="",
    )


def test_parse_team_requirement_requires_llm():
    with pytest.raises(LlmInvocationError, match="not available"):
        ParseTeamRequirementNode().run({"requirement": "Need a team", "llm": None})


def test_parse_team_requirement_maps_roles():
    output = ParseTeamRequirementChainOutput(
        roles=[
            ParsedRoleItem(
                role_key="role_1",
                role_title="Backend",
                skill_names=["Python"],
                skill_category=None,
                min_proficiency=ProficiencyLevel.ADVANCED,
            )
        ]
    )
    with patch(
        "server.ai.nodes.team_build_nodes.ParseTeamRequirementChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = output
        result = ParseTeamRequirementNode().run(
            {
                "llm": MagicMock(),
                "requirement": "Need a senior backend engineer",
                "max_roles": 10,
            }
        )

    assert result["llm_invoked"] is True
    assert len(result["parsed_roles"]) == 1
    assert result["parsed_roles"][0].role_key == "role_1"
    assert result["parsed_roles"][0].min_proficiency == ProficiencyLevel.ADVANCED


def test_parse_team_requirement_rejects_empty_roles():
    with patch(
        "server.ai.nodes.team_build_nodes.ParseTeamRequirementChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = ParseTeamRequirementChainOutput(
            roles=[]
        )
        with pytest.raises(InvalidTeamBuildRequestError, match="any roles"):
            ParseTeamRequirementNode().run(
                {
                    "llm": MagicMock(),
                    "requirement": "Build something somehow",
                    "max_roles": 10,
                }
            )


def test_parse_team_requirement_wraps_chain_failure():
    with patch(
        "server.ai.nodes.team_build_nodes.ParseTeamRequirementChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.side_effect = RuntimeError("bad")
        with pytest.raises(LlmInvocationError, match="parsing failed"):
            ParseTeamRequirementNode().run(
                {"llm": MagicMock(), "requirement": "Need a squad"}
            )


def test_solve_team_assignment_delegates_to_solver():
    solver = MagicMock()
    assignments = [_assignment()]
    solver.solve.return_value = (assignments, ["role_2"])
    roles = [_role(), _role("role_2")]
    state = {
        "parsed_roles": roles,
        "bench_candidates": [],
    }
    result = SolveTeamAssignmentNode(solver=solver).run(state)
    assert result["assignments"] == assignments
    assert result["unfilled_role_keys"] == ["role_2"]
    solver.solve.assert_called_once_with(roles, [])


@pytest.mark.asyncio
async def test_analyze_team_gaps_without_analyzer_returns_empty():
    result = await AnalyzeTeamGapsNode().run({"parsed_roles": [_role()]})
    assert result["gaps"] == []


@pytest.mark.asyncio
async def test_analyze_team_gaps_delegates():
    analyzer = AsyncMock()
    gaps = [
        RoleGapDTO(
            role_key="role_1",
            role_title="Backend",
            gap_type=TeamGapType.SKILL_ABSENCE,
            message="Missing Python",
        )
    ]
    analyzer.analyze.return_value = gaps
    result = await AnalyzeTeamGapsNode(gap_analyzer=analyzer).run(
        {
            "parsed_roles": [_role()],
            "unfilled_role_keys": ["role_1"],
            "diagnostics": [],
        }
    )
    assert result["gaps"] == gaps
    analyzer.analyze.assert_awaited_once()


def test_invoke_team_match_reason_skips_without_assignments():
    state = {"assignments": [], "llm": MagicMock()}
    assert InvokeTeamMatchReasonNode().run(state) is state


def test_invoke_team_match_reason_skips_without_llm():
    state = {"assignments": [_assignment()], "llm": None}
    assert InvokeTeamMatchReasonNode().run(state) is state


def test_invoke_team_match_reason_enriches_assignments():
    output = TeamMatchReasonChainOutput(
        items=[RoleReasonItem(role_key="role_1", reason="Great fit")]
    )
    with patch(
        "server.ai.nodes.team_build_nodes.TeamMatchReasonChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = output
        result = InvokeTeamMatchReasonNode().run(
            {
                "llm": MagicMock(),
                "requirement": "Need backend coverage",
                "parsed_roles": [_role()],
                "assignments": [_assignment()],
            }
        )

    assert result["llm_invoked"] is True
    assert result["assignments"][0].reason == "Great fit"


def test_invoke_team_match_reason_swallows_chain_errors():
    state = {
        "llm": MagicMock(),
        "requirement": "Need backend coverage",
        "parsed_roles": [_role()],
        "assignments": [_assignment()],
    }
    with patch(
        "server.ai.nodes.team_build_nodes.TeamMatchReasonChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.side_effect = RuntimeError("down")
        assert InvokeTeamMatchReasonNode().run(state) is state


def test_format_team_build_results_passthrough():
    state = {"assignments": []}
    assert FormatTeamBuildResultsNode().run(state) is state
