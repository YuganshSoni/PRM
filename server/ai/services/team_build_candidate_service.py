import logging

from server.ai.dto.team_build import SkillProficiencyDTO, TeamBuildCandidateDTO
from server.models.enums import ProficiencyLevel, SkillCategoryEnum
from server.repositories.timesheet_repository import TimesheetRepository
from server.services.manager_team_service import ManagerTeamService

logger = logging.getLogger(__name__)


class TeamBuildCandidateService:
    def __init__(
        self,
        manager_team_service: ManagerTeamService,
        timesheet_repository: TimesheetRepository,
    ) -> None:
        self._manager_team_service = manager_team_service
        self._timesheet_repository = timesheet_repository

    async def load_bench_for_manager(
        self, manager_resource_id: int
    ) -> list[TeamBuildCandidateDTO]:
        resources = await self._manager_team_service.list_bench_team_members(
            manager_resource_id,
            load_skills=True,
        )
        logger.info(
            "Team build candidate pool: manager_resource_id=%s resource_ids=%s",
            manager_resource_id,
            [resource.id for resource in resources],
        )
        candidates: list[TeamBuildCandidateDTO] = []
        for resource in resources:
            user = resource.user
            resource_name = user.full_name if user is not None else "Resource"
            skills = self._map_skills(resource)
            tags = await self._timesheet_repository.find_recent_activity_tags(
                resource.id
            )
            candidates.append(
                TeamBuildCandidateDTO(
                    resource_id=resource.id,
                    resource_name=resource_name,
                    skills=skills,
                    recent_activity_tags=tags,
                )
            )
        return candidates

    @staticmethod
    def _map_skills(resource) -> list[SkillProficiencyDTO]:
        mapped: list[SkillProficiencyDTO] = []
        for resource_skill in resource.skills:
            skill = getattr(resource_skill, "skill", None)
            category = getattr(skill, "category", None) if skill is not None else None
            if skill is None or category is None:
                continue
            mapped.append(
                SkillProficiencyDTO(
                    skill_name=skill.name,
                    category=SkillCategoryEnum(category.name),
                    proficiency=ProficiencyLevel(resource_skill.proficiency_level),
                )
            )
        return mapped
