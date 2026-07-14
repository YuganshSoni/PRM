from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class RiskSummaryChain:
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You summarize project risks for a manager in 3-6 plain-English sentences. "
                "Focus on risks and concerns only — not a raw data dump. "
                "Use only the facts provided.",
            ),
            ("human", "Project facts:\n{facts}"),
        ]
    )

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm | StrOutputParser()

    def invoke(self, facts_text: str) -> str:
        return self._chain.invoke({"facts": facts_text}).strip()
