from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.department import Department
from server.repositories.base_repository import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Department)

    async def find_or_create_by_name(self, name: str) -> Department:
        result = await self._session.execute(
            select(Department).where(Department.name == name)
        )
        department = result.scalar_one_or_none()
        if department is None:
            department = Department(name=name)
            department = await self.add(department)
        return department
