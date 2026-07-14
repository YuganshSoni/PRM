from server.ai.dto.team_build import (
    RoleAssignmentDTO,
    RoleRequirementDTO,
    TeamBuildCandidateDTO,
)
from server.ai.services.proficiency_matcher import ProficiencyMatcher


class TeamAssignmentSolver:
    def __init__(self, proficiency_matcher: ProficiencyMatcher | None = None) -> None:
        self._matcher = proficiency_matcher or ProficiencyMatcher()

    def solve(
        self,
        roles: list[RoleRequirementDTO],
        candidates: list[TeamBuildCandidateDTO],
    ) -> tuple[list[RoleAssignmentDTO], list[str]]:
        if not roles:
            return [], []

        best_assignments: list[tuple[RoleRequirementDTO, TeamBuildCandidateDTO, int]] = []
        best_score = -1

        def backtrack(
            index: int,
            used_ids: set[int],
            current: list[tuple[RoleRequirementDTO, TeamBuildCandidateDTO, int]],
            total_score: int,
        ) -> None:
            nonlocal best_assignments, best_score
            if index == len(roles):
                if total_score > best_score:
                    best_score = total_score
                    best_assignments = list(current)
                return

            role = roles[index]
            for candidate in candidates:
                if candidate.resource_id in used_ids:
                    continue
                score = self._matcher.score_role_match(role, candidate.skills)
                if score is None:
                    continue
                used_ids.add(candidate.resource_id)
                current.append((role, candidate, score))
                backtrack(index + 1, used_ids, current, total_score + score)
                current.pop()
                used_ids.remove(candidate.resource_id)

        backtrack(0, set(), [], 0)

        assignments = [
            RoleAssignmentDTO(
                role_key=role.role_key,
                role_title=role.role_title,
                resource_id=candidate.resource_id,
                resource_name=candidate.resource_name,
                match_score=score,
            )
            for role, candidate, score in best_assignments
        ]
        filled_keys = {assignment.role_key for assignment in assignments}
        unfilled = [role.role_key for role in roles if role.role_key not in filled_keys]
        return assignments, unfilled
