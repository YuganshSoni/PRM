from unittest.mock import MagicMock, patch

import pytest

from server.ai.nodes.risk_summary_nodes import InvokeRiskSummaryNode
from server.core.exceptions import LlmInvocationError


def test_invoke_risk_summary_requires_llm():
    with pytest.raises(LlmInvocationError, match="not available"):
        InvokeRiskSummaryNode().run(
            {
                "llm": None,
                "facts_text": "Risk: late milestone",
                "project_id": 1,
                "project_name": "Apollo",
            }
        )


def test_invoke_risk_summary_sets_summary():
    with patch(
        "server.ai.nodes.risk_summary_nodes.RiskSummaryChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.return_value = "Delivery risk from overdue milestones."
        result = InvokeRiskSummaryNode().run(
            {
                "llm": MagicMock(),
                "facts_text": "Overdue: Alpha",
                "project_id": 5,
                "project_name": "Apollo",
            }
        )

    assert result["summary"] == "Delivery risk from overdue milestones."
    assert result["llm_invoked"] is True
    chain_cls.return_value.invoke.assert_called_once_with("Overdue: Alpha")


def test_invoke_risk_summary_wraps_chain_errors():
    with patch(
        "server.ai.nodes.risk_summary_nodes.RiskSummaryChain"
    ) as chain_cls:
        chain_cls.return_value.invoke.side_effect = RuntimeError("offline")
        with pytest.raises(LlmInvocationError, match="invocation failed"):
            InvokeRiskSummaryNode().run(
                {
                    "llm": MagicMock(),
                    "facts_text": "facts",
                    "project_id": 1,
                    "project_name": "X",
                }
            )
