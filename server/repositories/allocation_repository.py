from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.allocation import Allocation
from server.repositories.base_repository import BaseRepository


class AllocationRepository(BaseRepository[Allocation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Allocation)

    async def find_active_by_employee(self, employee_id: int) -> list[Allocation]:
        today = date.today()
        result = await self._session.execute(
            select(Allocation)
            .where(
                Allocation.employee_id == employee_id,
                Allocation.to_date >= today,
            )
            .options(selectinload(Allocation.project))
            .order_by(Allocation.id)
        )
        return list(result.scalars().all())

    async def save(self, allocation: Allocation) -> Allocation:
        return await self.add(allocation)
