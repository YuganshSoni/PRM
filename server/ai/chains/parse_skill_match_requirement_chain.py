from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from server.models.enums import SkillCategoryEnum


class ParsedSkillMatchRequirementOutput(BaseModel):
    weekly_hours: int | None = Field(
        description="Hours per week if stated; null if full-time or unspecified"
    )
    skill_names: list[str] = Field(
        default_factory=list,
        description="Specific technologies or skills mentioned, e.g. React, Java, AWS",
    )
    role_title: str | None = Field(
        default=None,
        description="Role title if stated, e.g. Senior React Developer",
    )
    skill_category: SkillCategoryEnum | None = Field(
        default=None,
        description="BACKEND, FRONTEND, DEVOPS, QA, or OTHER when the role is broad",
    )
    seniority: str | None = Field(
        default=None,
        description="JUNIOR, MID, SENIOR, or null when not stated",
    )
    summary: str = Field(
        description="One-line interpretation of what the manager is asking for"
    )


class ParseSkillMatchRequirementChain:
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You extract structured staffing requirements from a manager message. "
                "Extract only what is explicitly stated or clearly implied. "
                "Do not invent skills or hours. "
                "If the message is generic with no role, technology, category, or hours, "
                "leave skill_names empty and role_title null. "
                "Normalize skill names (React, Java, AWS). "
                "Map broad roles to skill_category when no specific technology is named.",
            ),
            ("human", "Requirement:\n{requirement}"),
        ]
    )

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm.with_structured_output(
            ParsedSkillMatchRequirementOutput
        )

    def invoke(self, requirement: str) -> ParsedSkillMatchRequirementOutput:
        result = self._chain.invoke({"requirement": requirement})
        if isinstance(result, ParsedSkillMatchRequirementOutput):
            return result
        return ParsedSkillMatchRequirementOutput.model_validate(result)
