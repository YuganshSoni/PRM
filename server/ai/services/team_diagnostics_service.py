from server.ai.dto.team_build import SkillProficiencyDTO, TeamDiagnosticMemberDTO
from server.models.enums import ProficiencyLevel, ResourceStatusEnum, SkillCategoryEnum
from server.repositories.resource_repository import ResourceRepository


class TeamDiagnosticsService:
    def __init__(self, resource_repository: ResourceRepository) -> None:
        self._resource_repository = resource_repository

    async def load_for_manager(
        self, manager_resource_id: int
    ) -> list[TeamDiagnosticMemberDTO]:
        resources = await self._resource_repository.find_active_by_manager_id(
            manager_resource_id,
            load_skills=True,
        )
        members: list[TeamDiagnosticMemberDTO] = []
        for resource in resources:
            user = resource.user
            resource_name = user.full_name if user is not None else "Resource"
            status_name = (
                resource.resource_status.name
                if resource.resource_status is not None
                else ResourceStatusEnum.ALLOCATED.value
            )
            members.append(
                TeamDiagnosticMemberDTO(
                    resource_id=resource.id,
                    resource_name=resource_name,
                    is_bench=status_name == ResourceStatusEnum.BENCH.value,
                    skills=self._map_skills(resource),
                )
            )
        return members

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
