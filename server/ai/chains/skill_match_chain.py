from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from server.ai.dto.skill_match import SkillMatchCandidateDTO
from server.models.enums import SkillCategoryEnum


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
    skill_names: list[str]
    role_title: str | None
    skill_category: SkillCategoryEnum | None
    seniority: str | None
    summary: str


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
                "Requirement (original):\n{requirement}\n\n"
                "Parsed interpretation:\n"
                "- Summary: {summary}\n"
                "- Role: {role_title_label}\n"
                "- Skills: {skill_names_label}\n"
                "- Category: {skill_category_label}\n"
                "- Seniority: {seniority_label}\n"
                "- Weekly hours: {weekly_hours_label}\n\n"
                "Candidates:\n{candidates_text}",
            ),
        ]
    )

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm.with_structured_output(SkillMatchChainOutput)

    def invoke(self, payload: SkillMatchChainInput) -> SkillMatchChainOutput:
        result = self._chain.invoke(
            {
                "requirement": payload.requirement,
                "summary": payload.summary,
                "role_title_label": payload.role_title or "not specified",
                "skill_names_label": (
                    ", ".join(payload.skill_names)
                    if payload.skill_names
                    else "not specified"
                ),
                "skill_category_label": (
                    payload.skill_category.value
                    if payload.skill_category is not None
                    else "not specified"
                ),
                "seniority_label": payload.seniority or "not specified",
                "weekly_hours_label": (
                    str(payload.weekly_hours)
                    if payload.weekly_hours is not None
                    else "full-time"
                ),
                "candidates_text": "\n".join(
                    candidate.to_prompt_line() for candidate in payload.candidates
                ),
            }
        )
        if isinstance(result, SkillMatchChainOutput):
            return result
        return SkillMatchChainOutput.model_validate(result)
