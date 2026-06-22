from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from server.ai.dto.skill_match import SkillMatchCandidateDTO


class RankedMatchItem(BaseModel):
    resource_name: str = Field(description="Exact candidate name from the list")
    reason: str = Field(description="Plain-English reason for the ranking")
    rank: int = Field(description="1-based rank")


class SkillMatchChainOutput(BaseModel):
    items: list[RankedMatchItem]


@dataclass(frozen=True)
class SkillMatchChainInput:
    requirement: str
    candidates: list[SkillMatchCandidateDTO]
    weekly_hours: int | None


class SkillMatchChain:
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You rank employees for a project staffing requirement. "
                "Use ONLY the candidates provided. Return ranked matches with reasons. "
                "These are recommendations only — the manager must verify before allocating.",
            ),
            (
                "human",
                "Requirement:\n{requirement}\n\n"
                "Weekly hours requested: {weekly_hours_label}\n\n"
                "Candidates:\n{candidates_text}",
            ),
        ]
    )

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm.with_structured_output(SkillMatchChainOutput)

    def invoke(self, payload: SkillMatchChainInput) -> SkillMatchChainOutput:
        weekly_hours_label = (
            str(payload.weekly_hours) if payload.weekly_hours is not None else "full-time"
        )
        candidates_text = "\n".join(
            candidate.to_prompt_line() for candidate in payload.candidates
        )
        result = self._chain.invoke(
            {
                "requirement": payload.requirement,
                "weekly_hours_label": weekly_hours_label,
                "candidates_text": candidates_text,
            }
        )
        if isinstance(result, SkillMatchChainOutput):
            return result
        return SkillMatchChainOutput.model_validate(result)
