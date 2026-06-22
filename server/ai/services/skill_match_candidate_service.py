from collections import defaultdict

from server.ai.dto.skill_match import SkillMatchCandidateDTO
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.timesheet_repository import TimesheetRepository


class SkillMatchCandidateService:
    def __init__(
        self,
        resource_repository: ResourceRepository,
        allocation_repository: AllocationRepository,
        timesheet_repository: TimesheetRepository,
    ) -> None:
        self._resource_repository = resource_repository
        self._allocation_repository = allocation_repository
        self._timesheet_repository = timesheet_repository

    async def load_for_manager(
        self, manager_resource_id: int, *, max_weekly_hours: int
    ) -> list[SkillMatchCandidateDTO]:
        resources = await self._resource_repository.find_active_by_manager_id(
            manager_resource_id
        )
        if not resources:
            return []

        team_allocations = await self._allocation_repository.find_active_by_team(
            manager_resource_id
        )
        utilisation_map = self._sum_utilisation(team_allocations)

        candidates: list[SkillMatchCandidateDTO] = []
        for resource in resources:
            utilisation = utilisation_map.get(resource.id, 0)
            free_hours = max_weekly_hours * (100 - utilisation) / 100
            user = resource.user
            resource_name = user.full_name if user is not None else "Resource"
            skills = [
                resource_skill.skill.name
                for resource_skill in resource.skills
                if getattr(resource_skill, "skill", None) is not None
            ]
            tags = await self._timesheet_repository.find_recent_activity_tags(
                resource.id
            )
            candidates.append(
                SkillMatchCandidateDTO(
                    resource_id=resource.id,
                    resource_name=resource_name,
                    utilisation_percent=utilisation,
                    free_hours_per_week=free_hours,
                    skills=skills,
                    recent_activity_tags=tags,
                )
            )
        return candidates

    @staticmethod
    def _sum_utilisation(allocations) -> dict[int, int]:
        totals: dict[int, int] = defaultdict(int)
        for allocation in allocations:
            totals[allocation.resource_id] += allocation.utilisation_percent
        return dict(totals)
