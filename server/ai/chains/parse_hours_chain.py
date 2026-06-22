from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class ParsedHoursOutput(BaseModel):
    weekly_hours: int | None = Field(
        description="Hours per week requested, or null if full-time/open-ended"
    )


class ParseHoursChain:
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Extract weekly hours from the manager requirement. "
                "Return null if the request is full-time or does not specify weekly hours.",
            ),
            ("human", "{requirement}"),
        ]
    )

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm.with_structured_output(ParsedHoursOutput)

    def invoke(self, requirement: str) -> int | None:
        result = self._chain.invoke({"requirement": requirement})
        if isinstance(result, ParsedHoursOutput):
            return result.weekly_hours
        return result.get("weekly_hours")  # type: ignore[union-attr]
