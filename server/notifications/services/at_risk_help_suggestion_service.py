from server.ai.services.team_build_candidate_service import TeamBuildCandidateService
from server.repositories.project_repository import ProjectRepository


class AtRiskHelpSuggestionService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        bench_candidate_service: TeamBuildCandidateService,
    ) -> None:
        self._project_repository = project_repository
        self._bench_candidate_service = bench_candidate_service

    async def suggest(self, project_id: int, *, limit: int = 5) -> str:
        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None or project.manager_id is None:
            return "No bench suggestions available."

        candidates = await self._bench_candidate_service.load_bench_for_manager(
            project.manager_id
        )
        if not candidates:
            return "No bench employees available on the manager's team."

        lines: list[str] = []
        for candidate in candidates[:limit]:
            skills = ", ".join(
                f"{skill.skill_name} ({skill.proficiency.value})"
                for skill in candidate.skills
            ) or "no skills listed"
            lines.append(f"- {candidate.resource_name}: {skills}")
        return "\n".join(lines)
