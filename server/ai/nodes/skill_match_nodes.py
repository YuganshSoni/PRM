import math
import logging
from typing import TypedDict

from langchain_core.language_models.chat_models import BaseChatModel

from server.ai.chains.skill_match_chain import SkillMatchChain, SkillMatchChainInput
from server.ai.dto.skill_match import SkillMatchCandidateDTO, SkillMatchParsedRequirement
from server.core.exceptions import LlmInvocationError

logger = logging.getLogger(__name__)


class SkillMatchState(TypedDict, total=False):
    requirement: str
    project_id: int | None
    candidates: list[SkillMatchCandidateDTO]
    parsed_requirement: SkillMatchParsedRequirement
    filtered_candidates: list[SkillMatchCandidateDTO]
    weekly_hours: int | None
    max_weekly_hours: int
    ranked_items: list[dict]
    message: str | None
    llm_invoked: bool
    llm: BaseChatModel


class PreFilterCapacityNode:
    _EMPTY_MESSAGE = "No employees with enough free capacity for this requirement"

    def run(self, state: SkillMatchState) -> SkillMatchState:
        weekly_hours = state.get("weekly_hours")
        filtered: list[SkillMatchCandidateDTO] = []

        for candidate in state.get("candidates", []):
            if weekly_hours is None:
                if candidate.utilisation_percent < 100:
                    filtered.append(candidate)
            elif candidate.free_hours_per_week >= weekly_hours:
                filtered.append(candidate)

        update: SkillMatchState = {**state, "filtered_candidates": filtered}
        if not filtered:
            update["message"] = self._EMPTY_MESSAGE
            update["llm_invoked"] = False
            update["ranked_items"] = []
            logger.info(
                "Skill match pre-filter: 0 candidates (weekly_hours=%s pool=%s)",
                weekly_hours,
                len(state.get("candidates", [])),
            )
        else:
            logger.info(
                "Skill match pre-filter: %s candidates (weekly_hours=%s)",
                len(filtered),
                weekly_hours,
            )
        return update


class InvokeSkillMatchNode:
    def run(self, state: SkillMatchState) -> SkillMatchState:
        llm = state.get("llm")
        if llm is None:
            raise LlmInvocationError("LLM is not available for skill match")

        parsed = state["parsed_requirement"]
        try:
            output = SkillMatchChain(llm).invoke(
                SkillMatchChainInput(
                    requirement=state["requirement"],
                    candidates=state["filtered_candidates"],
                    weekly_hours=state.get("weekly_hours"),
                    skill_names=parsed.skill_names,
                    role_title=parsed.role_title,
                    skill_category=parsed.skill_category,
                    seniority=parsed.seniority,
                    summary=parsed.summary,
                )
            )
        except Exception as exc:
            logger.error("Skill match ranking LLM failed: %s", exc, exc_info=True)
            raise LlmInvocationError("Skill match LLM invocation failed") from exc

        name_to_candidate = {
            candidate.resource_name.lower(): candidate
            for candidate in state["filtered_candidates"]
        }
        ranked_items: list[dict] = []
        for item in sorted(output.items, key=lambda row: row.rank):
            candidate = name_to_candidate.get(item.resource_name.lower())
            if candidate is None:
                continue
            suggested_pct = None
            weekly_hours = state.get("weekly_hours")
            max_weekly = state["max_weekly_hours"]
            if weekly_hours is not None and max_weekly > 0:
                suggested_pct = min(
                    100 - candidate.utilisation_percent,
                    max(1, math.ceil(weekly_hours / max_weekly * 100)),
                )
            ranked_items.append(
                {
                    "resource_id": candidate.resource_id,
                    "resource_name": candidate.resource_name,
                    "reason": item.reason,
                    "rank": item.rank,
                    "free_hours_per_week": candidate.free_hours_per_week,
                    "suggested_utilisation_percent": suggested_pct,
                }
            )

        logger.info("Skill match ranking complete: ranked_items=%s", len(ranked_items))
        return {**state, "ranked_items": ranked_items, "llm_invoked": True}


class FormatSkillMatchResultsNode:
    def run(self, state: SkillMatchState) -> SkillMatchState:
        return state
