from server.ai.dto.team_build import (
    RoleGapDTO,
    RoleRequirementDTO,
    TeamDiagnosticMemberDTO,
    TeamGapType,
)
from server.ai.services.availability_date_service import AvailabilityDateService
from server.ai.services.proficiency_matcher import ProficiencyMatcher


class TeamGapAnalyzer:
    def __init__(
        self,
        proficiency_matcher: ProficiencyMatcher | None = None,
        availability_date_service: AvailabilityDateService | None = None,
    ) -> None:
        self._matcher = proficiency_matcher or ProficiencyMatcher()
        self._availability = availability_date_service

    async def analyze(
        self,
        roles: list[RoleRequirementDTO],
        unfilled_role_keys: list[str],
        diagnostics: list[TeamDiagnosticMemberDTO],
    ) -> list[RoleGapDTO]:
        role_by_key = {role.role_key: role for role in roles}
        gaps: list[RoleGapDTO] = []

        for role_key in unfilled_role_keys:
            role = role_by_key[role_key]
            skilled = [
                member
                for member in diagnostics
                if self._matcher.meets_role(role, member.skills)
            ]
            if not skilled:
                skill_label = ", ".join(role.skill_names) or self._matcher.category_label(
                    role.skill_category
                )
                gaps.append(
                    RoleGapDTO(
                        role_key=role.role_key,
                        role_title=role.role_title,
                        gap_type=TeamGapType.SKILL_ABSENCE,
                        message=(
                            f"No one on your team has {skill_label} at "
                            f"{role.min_proficiency.value} — consider hiring or training."
                        ),
                    )
                )
                continue

            allocated = [member for member in skilled if not member.is_bench]
            if not allocated:
                gaps.append(
                    RoleGapDTO(
                        role_key=role.role_key,
                        role_title=role.role_title,
                        gap_type=TeamGapType.SKILL_ABSENCE,
                        message=(
                            f"No bench employee matches {role.role_title} requirements."
                        ),
                    )
                )
                continue

            hint = allocated[0]
            available_from = None
            if self._availability is not None:
                available_from = await self._availability.compute_available_from(
                    hint.resource_id
                )
            date_text = (
                available_from.isoformat() if available_from is not None else "unknown"
            )
            gaps.append(
                RoleGapDTO(
                    role_key=role.role_key,
                    role_title=role.role_title,
                    gap_type=TeamGapType.AVAILABILITY_CONFLICT,
                    message=(
                        f"{hint.resource_name} has the required skills but is allocated "
                        f"elsewhere — available from {date_text}."
                    ),
                    available_from=available_from,
                    candidate_hint_name=hint.resource_name,
                )
            )

        return gaps
