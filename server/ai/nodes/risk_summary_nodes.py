from typing import TypedDict

from langchain_core.language_models.chat_models import BaseChatModel

from server.ai.chains.risk_summary_chain import RiskSummaryChain
from server.core.exceptions import LlmInvocationError


class RiskSummaryState(TypedDict, total=False):
    project_id: int
    project_name: str
    facts_text: str
    summary: str
    llm_invoked: bool
    llm: BaseChatModel


class InvokeRiskSummaryNode:
    def run(self, state: RiskSummaryState) -> RiskSummaryState:
        llm = state.get("llm")
        if llm is None:
            raise LlmInvocationError("LLM is not available for risk summary")

        try:
            summary = RiskSummaryChain(llm).invoke(state["facts_text"])
        except Exception as exc:
            raise LlmInvocationError("Risk summary LLM invocation failed") from exc

        return {**state, "summary": summary, "llm_invoked": True}
