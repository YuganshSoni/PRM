from server.core.exceptions import (
    DuplicateSkillError,
    EmployeeNotFoundError,
    SkillNotFoundError,
)
from server.models.employee_skill import EmployeeSkill
from server.repositories.employee_repository import EmployeeRepository
from server.repositories.skill_repository import SkillRepository
from server.schemas.requests.skill import AddSkillRequest, UpdateSkillProficiencyRequest


class SkillService:
    def __init__(
        self,
        skill_repository: SkillRepository,
        employee_repository: EmployeeRepository,
    ) -> None:
        self._skill_repository = skill_repository
        self._employee_repository = employee_repository

    async def add_skill(
        self, employee_id: int, dto: AddSkillRequest
    ) -> EmployeeSkill:
        await self._require_employee(employee_id)

        existing = await self._skill_repository.find_by_employee_and_name(
            employee_id, dto.skill_name
        )
        if existing is not None:
            raise DuplicateSkillError("Skill already exists for this employee")

        skill = EmployeeSkill(
            employee_id=employee_id,
            skill_name=dto.skill_name,
            category=dto.category,
            proficiency_level=dto.proficiency_level,
        )
        return await self._skill_repository.save(skill)

    async def list_skills(self, employee_id: int) -> list[EmployeeSkill]:
        await self._require_employee(employee_id)
        return await self._skill_repository.find_by_employee_id(employee_id)

    async def update_proficiency(
        self, skill_id: int, dto: UpdateSkillProficiencyRequest
    ) -> EmployeeSkill:
        skill = await self._skill_repository.get_by_id(skill_id)
        if skill is None:
            raise SkillNotFoundError("Skill not found")
        skill.proficiency_level = dto.proficiency_level
        return await self._skill_repository.save(skill)

    async def remove_skill(self, skill_id: int) -> None:
        skill = await self._skill_repository.get_by_id(skill_id)
        if skill is None:
            raise SkillNotFoundError("Skill not found")
        await self._skill_repository.delete(skill)

    async def _require_employee(self, employee_id: int) -> None:
        employee = await self._employee_repository.get_by_id(employee_id)
        if employee is None:
            raise EmployeeNotFoundError("Employee not found")
