from unittest.mock import MagicMock, patch

import pytest

from server.ai.chains.skill_match_chain import RankedMatchItem, SkillMatchChainOutput
from server.ai.dto.skill_match import SkillMatchCandidateDTO, SkillMatchParsedRequirement
from server.ai.nodes.skill_match_nodes import (
    FormatSkillMatchResultsNode,
    InvokeSkillMatchNode,
    PreFilterCapacityNode,
)
from server.core.exceptions import LlmInvocationError


def _candidate(
    resource_id: int,
    name: str,
    *,
    utilisation: int = 50,
    free_hours: float = 20.0,
) -> SkillMatchCandidateDTO:
    return SkillMatchCandidateDTO(
        resource_id=resource_id,
        resource_name=name,
        utilisation_percent=utilisation,
        free_hours_per_week=free_hours,
        skills=["Python"],
        recent_activity_tags=[],
    )


def _parsed() -> SkillMatchParsedRequirement:
    return SkillMatchParsedRequirement(
        weekly_hours=20,
        skill_names=["Python"],
        role_title="Backend",
        skill_category=None,
        seniority=None,
        summary="Need backend help",
        is_actionable=True,
    )


def test_pre_filter_keeps_candidates_with_enough_hours():
    state = {
        "candidates": [
            _candidate(1, "Ada", free_hours=25),
            _candidate(2, "Bob", free_hours=10),
        ],
        "weekly_hours": 20,
    }
    result = PreFilterCapacityNode().run(state)
    assert len(result["filtered_candidates"]) == 1
    assert result["filtered_candidates"][0].resource_name == "Ada"
    assert "message" not in result or result.get("message") is None


def test_pre_filter_without_weekly_hours_keeps_under_full_utilisation():
    state = {
        "candidates": [
            _candidate(1, "Ada", utilisation=99),
            _candidate(2, "Bob", utilisation=100),
        ],
        "weekly_hours": None,
    }
    result = PreFilterCapacityNode().run(state)
    assert [c.resource_name for c in result["filtered_candidates"]] == ["Ada"]


def test_pre_filter_empty_sets_message_and_skips_llm():
    state = {
        "candidates": [_candidate(1, "Ada", free_hours=5)],
        "weekly_hours": 20,
    }
    result = PreFilterCapacityNode().run(state)
    assert result["filtered_candidates"] == []
    assert result["message"] == PreFilterCapacityNode._EMPTY_MESSAGE
    assert result["llm_invoked"] is False
    assert result["ranked_items"] == []


def test_invoke_skill_match_requires_llm():
    with pytest.raises(LlmInvocationError, match="not available"):
        InvokeSkillMatchNode().run(
            {
                "llm": None,
                "parsed_requirement": _parsed(),
                "filtered_candidates": [],
                "requirement": "Need help",
                "max_weekly_hours": 40,
            }
        )


def test_invoke_skill_match_maps_ranked_output():
    llm = MagicMock()
    candidates = [_candidate(1, "Ada", utilisation=25, free_hours=30)]
    output = SkillMatchChainOutput(
        items=[
            RankedMatchItem(resource_name="Ada", reason="Strong Python", rank=1),
            RankedMatchItem(resource_name="Unknown", reason="skip", rank=2),
        ]
    )
    with patch(
        "server.ai.nodes.skill_match_nodes.SkillMatchChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = output
        result = InvokeSkillMatchNode().run(
            {
                "llm": llm,
                "requirement": "Need a Python engineer for 20h",
                "parsed_requirement": _parsed(),
                "filtered_candidates": candidates,
                "weekly_hours": 20,
                "max_weekly_hours": 40,
            }
        )

    assert result["llm_invoked"] is True
    assert len(result["ranked_items"]) == 1
    item = result["ranked_items"][0]
    assert item["resource_id"] == 1
    assert item["reason"] == "Strong Python"
    assert item["rank"] == 1
    assert item["suggested_utilisation_percent"] == 50


def test_invoke_skill_match_wraps_chain_errors():
    with patch(
        "server.ai.nodes.skill_match_nodes.SkillMatchChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.side_effect = RuntimeError("boom")
        with pytest.raises(LlmInvocationError, match="invocation failed"):
            InvokeSkillMatchNode().run(
                {
                    "llm": MagicMock(),
                    "requirement": "Need help for staffing",
                    "parsed_requirement": _parsed(),
                    "filtered_candidates": [_candidate(1, "Ada")],
                    "max_weekly_hours": 40,
                }
            )


def test_format_skill_match_results_passthrough():
    state = {"ranked_items": [{"rank": 1}], "llm_invoked": True}
    assert FormatSkillMatchResultsNode().run(state) is state
