from server.ai.dto.team_build import SkillProficiencyDTO, TeamBuildCandidateDTO
from server.models.enums import ProficiencyLevel, ResourceStatusEnum, SkillCategoryEnum
from server.repositories.resource_repository import ResourceRepository
from server.repositories.timesheet_repository import TimesheetRepository


class TeamBuildCandidateService:
    def __init__(
        self,
        resource_repository: ResourceRepository,
        timesheet_repository: TimesheetRepository,
    ) -> None:
        self._resource_repository = resource_repository
        self._timesheet_repository = timesheet_repository

    async def load_bench_for_manager(
        self, manager_resource_id: int
    ) -> list[TeamBuildCandidateDTO]:
        resources = await self._resource_repository.find_by_manager_and_status(
            manager_resource_id,
            ResourceStatusEnum.BENCH,
            load_skills=True,
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
