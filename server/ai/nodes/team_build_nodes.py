from typing import TypedDict

from langchain_core.language_models.chat_models import BaseChatModel

from server.ai.chains.parse_team_requirement_chain import (
    ParseTeamRequirementChain,
    ParseTeamRequirementChainInput,
)
from server.ai.chains.team_match_reason_chain import (
    TeamMatchReasonChain,
    TeamMatchReasonChainInput,
)
from server.ai.dto.team_build import (
    RoleAssignmentDTO,
    RoleGapDTO,
    RoleRequirementDTO,
    TeamBuildCandidateDTO,
    TeamDiagnosticMemberDTO,
)
from server.ai.services.team_assignment_solver import TeamAssignmentSolver
from server.ai.services.team_gap_analyzer import TeamGapAnalyzer
from server.core.exceptions import InvalidTeamBuildRequestError, LlmInvocationError


MAX_TEAM_ROLES = 10


class TeamBuildState(TypedDict, total=False):
    requirement: str
    project_id: int
    max_roles: int
    bench_candidates: list[TeamBuildCandidateDTO]
    diagnostics: list[TeamDiagnosticMemberDTO]
    parsed_roles: list[RoleRequirementDTO]
    assignments: list[RoleAssignmentDTO]
    unfilled_role_keys: list[str]
    gaps: list[RoleGapDTO]
    llm_invoked: bool
    llm: BaseChatModel


class ParseTeamRequirementNode:
    def run(self, state: TeamBuildState) -> TeamBuildState:
        llm = state.get("llm")
        if llm is None:
            raise LlmInvocationError("LLM is not available for team build")

        try:
            parsed = ParseTeamRequirementChain(llm).invoke(
                ParseTeamRequirementChainInput(
                    requirement=state["requirement"],
                    max_roles=state.get("max_roles", MAX_TEAM_ROLES),
                )
            )
        except Exception as exc:
            raise LlmInvocationError("Team requirement parsing failed") from exc

        roles = [
            RoleRequirementDTO(
                role_key=item.role_key,
                role_title=item.role_title,
                skill_names=item.skill_names,
                skill_category=item.skill_category,
                min_proficiency=item.min_proficiency,
            )
            for item in parsed.roles[: state.get("max_roles", MAX_TEAM_ROLES)]
        ]
        if not roles:
            raise InvalidTeamBuildRequestError(
                "Could not identify any roles in the requirement"
            )
        if len(roles) > state.get("max_roles", MAX_TEAM_ROLES):
            raise InvalidTeamBuildRequestError(
                f"A maximum of {state.get('max_roles', MAX_TEAM_ROLES)} roles is allowed"
            )

        return {**state, "parsed_roles": roles, "llm_invoked": True}


class SolveTeamAssignmentNode:
    def __init__(self, solver: TeamAssignmentSolver | None = None) -> None:
        self._solver = solver or TeamAssignmentSolver()

    def run(self, state: TeamBuildState) -> TeamBuildState:
        assignments, unfilled = self._solver.solve(
            state.get("parsed_roles", []),
            state.get("bench_candidates", []),
        )
        return {
            **state,
            "assignments": assignments,
            "unfilled_role_keys": unfilled,
        }


class AnalyzeTeamGapsNode:
    def __init__(self, gap_analyzer: TeamGapAnalyzer | None = None) -> None:
        self._gap_analyzer = gap_analyzer

    async def run(self, state: TeamBuildState) -> TeamBuildState:
        if self._gap_analyzer is None:
            return {**state, "gaps": []}

        gaps = await self._gap_analyzer.analyze(
            state.get("parsed_roles", []),
            state.get("unfilled_role_keys", []),
            state.get("diagnostics", []),
        )
        return {**state, "gaps": gaps}


class InvokeTeamMatchReasonNode:
    def run(self, state: TeamBuildState) -> TeamBuildState:
        assignments = state.get("assignments", [])
        if not assignments:
            return state

        llm = state.get("llm")
        if llm is None:
            return state

        try:
            output = TeamMatchReasonChain(llm).invoke(
                TeamMatchReasonChainInput(
                    requirement=state["requirement"],
                    roles=state.get("parsed_roles", []),
                    assignments=assignments,
                )
            )
        except Exception:
            return state

        reason_by_key = {item.role_key: item.reason for item in output.items}
        enriched = [
            RoleAssignmentDTO(
                role_key=assignment.role_key,
                role_title=assignment.role_title,
                resource_id=assignment.resource_id,
                resource_name=assignment.resource_name,
                match_score=assignment.match_score,
                reason=reason_by_key.get(
                    assignment.role_key,
                    "Matched required skills on bench.",
                ),
            )
            for assignment in assignments
        ]
        return {**state, "assignments": enriched, "llm_invoked": True}


class FormatTeamBuildResultsNode:
    def run(self, state: TeamBuildState) -> TeamBuildState:
        return state
