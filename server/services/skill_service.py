from server.core.exceptions import (
    DuplicateSkillError,
    EmployeeNotFoundError,
    SkillNotFoundError,
)
from server.models.resource_skill import ResourceSkill
from server.repositories.master_skill_repository import MasterSkillRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.skill_repository import SkillRepository
from server.schemas.requests.skill import AddSkillRequest, UpdateSkillProficiencyRequest


class SkillService:
    def __init__(
        self,
        skill_repository: SkillRepository,
        resource_repository: ResourceRepository,
        master_skill_repository: MasterSkillRepository,
    ) -> None:
        self._skill_repository = skill_repository
        self._resource_repository = resource_repository
        self._master_skill_repository = master_skill_repository

    async def add_skill(
        self, resource_id: int, dto: AddSkillRequest
    ) -> ResourceSkill:
        await self._require_resource(resource_id)

        existing = await self._skill_repository.find_by_resource_and_name(
            resource_id, dto.skill_name
        )
        if existing is not None:
            raise DuplicateSkillError("Skill already exists for this resource")

        master_skill = await self._master_skill_repository.find_or_create(
            dto.skill_name, dto.category.value
        )

        skill = ResourceSkill(
            resource_id=resource_id,
            skill_id=master_skill.id,
            proficiency_level=dto.proficiency_level.value,
        )
        saved = await self._skill_repository.save(skill)
        loaded = await self._skill_repository.get_by_id_with_relations(saved.id)
        if loaded is None:
            raise SkillNotFoundError("Skill not found")
        return loaded

    async def list_skills(self, resource_id: int) -> list[ResourceSkill]:
        await self._require_resource(resource_id)
        return await self._skill_repository.find_by_resource_id(resource_id)

    async def update_proficiency(
        self, skill_id: int, dto: UpdateSkillProficiencyRequest
    ) -> ResourceSkill:
        skill = await self._skill_repository.get_by_id(skill_id)
        if skill is None:
            raise SkillNotFoundError("Skill not found")
        skill.proficiency_level = dto.proficiency_level.value
        saved = await self._skill_repository.save(skill)
        loaded = await self._skill_repository.get_by_id_with_relations(saved.id)
        if loaded is None:
            raise SkillNotFoundError("Skill not found")
        return loaded

    async def remove_skill(self, skill_id: int) -> None:
        skill = await self._skill_repository.get_by_id(skill_id)
        if skill is None:
            raise SkillNotFoundError("Skill not found")
        await self._skill_repository.delete(skill)

    async def _require_resource(self, resource_id: int) -> None:
        resource = await self._resource_repository.get_by_id(resource_id)
        if resource is None:
            raise EmployeeNotFoundError("Resource not found")
