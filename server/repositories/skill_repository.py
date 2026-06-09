from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.employee_skill import EmployeeSkill
from server.repositories.base_repository import BaseRepository


class SkillRepository(BaseRepository[EmployeeSkill]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeSkill)

    async def find_by_employee_id(self, employee_id: int) -> list[EmployeeSkill]:
        result = await self._session.execute(
            select(EmployeeSkill)
            .where(EmployeeSkill.employee_id == employee_id)
            .order_by(EmployeeSkill.id)
        )
        return list(result.scalars().all())

    async def find_by_employee_and_name(
        self, employee_id: int, skill_name: str
    ) -> EmployeeSkill | None:
        result = await self._session.execute(
            select(EmployeeSkill).where(
                EmployeeSkill.employee_id == employee_id,
                EmployeeSkill.skill_name == skill_name,
            )
        )
        return result.scalar_one_or_none()

    async def save(self, skill: EmployeeSkill) -> EmployeeSkill:
        return await self.add(skill)
