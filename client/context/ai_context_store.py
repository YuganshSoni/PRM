from client.context.ai_flow_context import AiFlowContext


class AiContextStore:
    def __init__(self) -> None:
        self._context: AiFlowContext | None = None

    def set(self, context: AiFlowContext) -> None:
        self._context = context

    def consume(self) -> AiFlowContext | None:
        context = self._context
        self._context = None
        return context
