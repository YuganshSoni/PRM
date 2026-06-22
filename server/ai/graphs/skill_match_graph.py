from langgraph.graph import END, StateGraph

from server.ai.nodes.skill_match_nodes import (
    FormatSkillMatchResultsNode,
    InvokeSkillMatchNode,
    ParseWeeklyHoursNode,
    PreFilterCapacityNode,
    SkillMatchState,
)


class SkillMatchGraphBuilder:
    def __init__(self) -> None:
        self._parse_node = ParseWeeklyHoursNode()
        self._filter_node = PreFilterCapacityNode()
        self._invoke_node = InvokeSkillMatchNode()
        self._format_node = FormatSkillMatchResultsNode()

    def build(self):
        graph = StateGraph(SkillMatchState)
        graph.add_node("parse_hours", self._parse_node.run)
        graph.add_node("pre_filter", self._filter_node.run)
        graph.add_node("invoke_match", self._invoke_node.run)
        graph.add_node("format_results", self._format_node.run)

        graph.set_entry_point("parse_hours")
        graph.add_edge("parse_hours", "pre_filter")
        graph.add_conditional_edges(
            "pre_filter",
            self._route_after_filter,
            {
                "invoke": "invoke_match",
                "empty": "format_results",
            },
        )
        graph.add_edge("invoke_match", "format_results")
        graph.add_edge("format_results", END)
        return graph.compile()

    @staticmethod
    def _route_after_filter(state: SkillMatchState) -> str:
        if not state.get("filtered_candidates"):
            return "empty"
        return "invoke"


class SkillMatchGraphRunner:
    def __init__(self, builder: SkillMatchGraphBuilder | None = None) -> None:
        self._compiled = (builder or SkillMatchGraphBuilder()).build()

    def invoke(self, state: SkillMatchState) -> SkillMatchState:
        return self._compiled.invoke(state)
