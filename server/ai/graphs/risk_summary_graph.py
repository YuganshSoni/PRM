from langgraph.graph import END, StateGraph

from server.ai.nodes.risk_summary_nodes import InvokeRiskSummaryNode, RiskSummaryState


class RiskSummaryGraphBuilder:
    def __init__(self) -> None:
        self._invoke_node = InvokeRiskSummaryNode()

    def build(self):
        graph = StateGraph(RiskSummaryState)
        graph.add_node("invoke_summary", self._invoke_node.run)
        graph.set_entry_point("invoke_summary")
        graph.add_edge("invoke_summary", END)
        return graph.compile()


class RiskSummaryGraphRunner:
    def __init__(self, builder: RiskSummaryGraphBuilder | None = None) -> None:
        self._compiled = (builder or RiskSummaryGraphBuilder()).build()

    def invoke(self, state: RiskSummaryState) -> RiskSummaryState:
        return self._compiled.invoke(state)
