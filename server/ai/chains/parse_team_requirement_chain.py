from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from server.models.enums import ProficiencyLevel, SkillCategoryEnum


class ParsedRoleItem(BaseModel):
    role_key: str = Field(description="Stable id such as role_1, role_2")
    role_title: str = Field(description="Human-readable role title")
    skill_names: list[str] = Field(
        default_factory=list,
        description="Required master skill names when known, else empty",
    )
    skill_category: SkillCategoryEnum | None = Field(
        default=None,
        description="BACKEND, FRONTEND, DEVOPS, QA, or OTHER when role is category-based",
    )
    min_proficiency: ProficiencyLevel = Field(
        description="Required proficiency: BEGINNER, INTERMEDIATE, or ADVANCED"
    )


class ParseTeamRequirementChainOutput(BaseModel):
    roles: list[ParsedRoleItem]


@dataclass(frozen=True)
class ParseTeamRequirementChainInput:
    requirement: str
    max_roles: int


class ParseTeamRequirementChain:
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You extract structured staffing roles from a manager's team requirement. "
                "Return up to {max_roles} roles. "
                "Map senior/expert roles to ADVANCED, mid-level to INTERMEDIATE, junior to BEGINNER. "
                "Use skill_names when a specific technology is named (e.g. Java, React). "
                "Use skill_category when the role is broad (e.g. DevOps Engineer -> DEVOPS, QA Tester -> QA). "
                "These are recommendations only.",
            ),
            ("human", "Team requirement:\n{requirement}"),
        ]
    )

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm.with_structured_output(
            ParseTeamRequirementChainOutput
        )

    def invoke(
        self, payload: ParseTeamRequirementChainInput
    ) -> ParseTeamRequirementChainOutput:
        result = self._chain.invoke(
            {
                "requirement": payload.requirement,
                "max_roles": payload.max_roles,
            }
        )
        if isinstance(result, ParseTeamRequirementChainOutput):
            return result
        return ParseTeamRequirementChainOutput.model_validate(result)
