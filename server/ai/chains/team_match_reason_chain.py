from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from server.ai.dto.team_build import RoleAssignmentDTO, RoleRequirementDTO


class RoleReasonItem(BaseModel):
    role_key: str
    reason: str


class TeamMatchReasonChainOutput(BaseModel):
    items: list[RoleReasonItem]


@dataclass(frozen=True)
class TeamMatchReasonChainInput:
    requirement: str
    roles: list[RoleRequirementDTO]
    assignments: list[RoleAssignmentDTO]


class TeamMatchReasonChain:
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Write one concise plain-English reason per assigned role. "
                "Use only the assignment facts provided.",
            ),
            (
                "human",
                "Requirement:\n{requirement}\n\nAssignments:\n{assignments_text}",
            ),
        ]
    )

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm.with_structured_output(
            TeamMatchReasonChainOutput
        )

    def invoke(self, payload: TeamMatchReasonChainInput) -> TeamMatchReasonChainOutput:
        assignments_text = "\n".join(
            f"{assignment.role_title} -> {assignment.resource_name}"
            for assignment in payload.assignments
        )
        result = self._chain.invoke(
            {
                "requirement": payload.requirement,
                "assignments_text": assignments_text,
            }
        )
        if isinstance(result, TeamMatchReasonChainOutput):
            return result
        return TeamMatchReasonChainOutput.model_validate(result)
