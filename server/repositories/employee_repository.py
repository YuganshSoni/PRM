from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.employee import Employee
from server.models.enums import EmployeeStatus
from server.repositories.base_repository import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Employee)

    async def find_by_user_id(self, user_id: int) -> Employee | None:
        result = await self._session.execute(
            select(Employee).where(Employee.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_employees(
        self,
        *,
        status: EmployeeStatus | None,
        department: str | None,
        limit: int,
        offset: int,
    ) -> list[Employee]:
        query = select(Employee).where(Employee.is_active.is_(True))
        if status is not None:
            query = query.where(Employee.status == status)
        if department is not None:
            query = query.where(Employee.department == department)
        query = query.order_by(Employee.id).limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_active_employees(
        self,
        *,
        status: EmployeeStatus | None = None,
        department: str | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(Employee)
            .where(Employee.is_active.is_(True))
        )
        if status is not None:
            query = query.where(Employee.status == status)
        if department is not None:
            query = query.where(Employee.department == department)
        result = await self._session.execute(query)
        return int(result.scalar_one())

    async def count_by_status(self, status: EmployeeStatus) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Employee)
            .where(Employee.is_active.is_(True), Employee.status == status)
        )
        return int(result.scalar_one())

    async def save(self, employee: Employee) -> Employee:
        return await self.add(employee)
