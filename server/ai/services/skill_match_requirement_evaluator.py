from server.ai.chains.parse_skill_match_requirement_chain import (
    ParsedSkillMatchRequirementOutput,
)
from server.ai.dto.skill_match import SkillMatchParsedRequirement


class SkillMatchRequirementEvaluator:
    _GENERIC_ROLE_TITLES = frozenset(
        {
            "developer",
            "engineer",
            "resource",
            "employee",
            "someone",
            "person",
            "help",
            "team member",
            "staff",
            "anybody",
            "anyone",
            "somebody",
        }
    )

    def evaluate(
        self,
        parsed: ParsedSkillMatchRequirementOutput,
        *,
        max_weekly_hours: int,
    ) -> SkillMatchParsedRequirement:
        skill_names = self._normalize_skills(parsed.skill_names)
        role_title = self._normalize_role_title(parsed.role_title)
        weekly_hours = self._normalize_weekly_hours(
            parsed.weekly_hours, max_weekly_hours=max_weekly_hours
        )
        skill_category = parsed.skill_category
        seniority = self._normalize_seniority(parsed.seniority)
        summary = parsed.summary.strip() or "Unspecified staffing requirement"

        is_actionable = bool(
            skill_names
            or weekly_hours is not None
            or skill_category is not None
            or self._is_concrete_role(role_title)
        )

        return SkillMatchParsedRequirement(
            weekly_hours=weekly_hours,
            skill_names=skill_names,
            role_title=role_title,
            skill_category=skill_category,
            seniority=seniority,
            summary=summary,
            is_actionable=is_actionable,
        )

    def _normalize_skills(self, skill_names: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for name in skill_names:
            cleaned = name.strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized

    def _normalize_role_title(self, role_title: str | None) -> str | None:
        if role_title is None:
            return None
        cleaned = role_title.strip()
        return cleaned or None

    def _normalize_weekly_hours(
        self, weekly_hours: int | None, *, max_weekly_hours: int
    ) -> int | None:
        if weekly_hours is None:
            return None
        if weekly_hours <= 0 or weekly_hours > max_weekly_hours:
            return None
        return weekly_hours

    def _normalize_seniority(self, seniority: str | None) -> str | None:
        if seniority is None:
            return None
        cleaned = seniority.strip().upper()
        return cleaned or None

    def _is_concrete_role(self, role_title: str | None) -> bool:
        if role_title is None:
            return False
        normalized = role_title.casefold().strip()
        if not normalized:
            return False
        if normalized in self._GENERIC_ROLE_TITLES:
            return False
        tokens = {token.strip() for token in normalized.split() if token.strip()}
        if tokens and tokens.issubset(self._GENERIC_ROLE_TITLES):
            return False
        return True
