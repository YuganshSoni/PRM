from langgraph.graph import END, StateGraph

from server.ai.nodes.team_build_nodes import (
    AnalyzeTeamGapsNode,
    FormatTeamBuildResultsNode,
    InvokeTeamMatchReasonNode,
    ParseTeamRequirementNode,
    SolveTeamAssignmentNode,
    TeamBuildState,
)
from server.ai.services.team_gap_analyzer import TeamGapAnalyzer


class TeamBuildGraphBuilder:
    def __init__(self, gap_analyzer: TeamGapAnalyzer | None = None) -> None:
        self._parse_node = ParseTeamRequirementNode()
        self._solve_node = SolveTeamAssignmentNode()
        self._gap_node = AnalyzeTeamGapsNode(gap_analyzer)
        self._reason_node = InvokeTeamMatchReasonNode()
        self._format_node = FormatTeamBuildResultsNode()

    def build(self):
        graph = StateGraph(TeamBuildState)
        graph.add_node("parse_requirement", self._parse_node.run)
        graph.add_node("solve_assignment", self._solve_node.run)
        graph.add_node("analyze_gaps", self._run_analyze_gaps)
        graph.add_node("invoke_reasons", self._reason_node.run)
        graph.add_node("format_results", self._format_node.run)

        graph.set_entry_point("parse_requirement")
        graph.add_edge("parse_requirement", "solve_assignment")
        graph.add_edge("solve_assignment", "analyze_gaps")
        graph.add_conditional_edges(
            "analyze_gaps",
            self._route_after_gaps,
            {
                "reasons": "invoke_reasons",
                "format": "format_results",
            },
        )
        graph.add_edge("invoke_reasons", "format_results")
        graph.add_edge("format_results", END)
        return graph.compile()

    async def _run_analyze_gaps(self, state: TeamBuildState) -> TeamBuildState:
        return await self._gap_node.run(state)

    @staticmethod
    def _route_after_gaps(state: TeamBuildState) -> str:
        if state.get("assignments"):
            return "reasons"
        return "format"


class TeamBuildGraphRunner:
    def __init__(
        self,
        builder: TeamBuildGraphBuilder | None = None,
        gap_analyzer: TeamGapAnalyzer | None = None,
    ) -> None:
        self._compiled = (builder or TeamBuildGraphBuilder(gap_analyzer)).build()

    async def invoke(self, state: TeamBuildState) -> TeamBuildState:
        return await self._compiled.ainvoke(state)
