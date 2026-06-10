from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.allocation import Allocation
from server.models.employee import Employee
from server.models.project import Project
from server.repositories.base_repository import BaseRepository


class AllocationRepository(BaseRepository[Allocation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Allocation)

    async def find_active_by_team(self, manager_employee_id: int) -> list[Allocation]:
        today = date.today()
        result = await self._session.execute(
            select(Allocation)
            .join(Employee, Allocation.employee_id == Employee.id)
            .where(
                Employee.manager_id == manager_employee_id,
                Allocation.to_date >= today,
            )
            .options(
                selectinload(Allocation.employee),
                selectinload(Allocation.project),
            )
            .order_by(Allocation.employee_id, Allocation.id)
        )
        return list(result.scalars().unique().all())

    async def find_overlapping(
        self, employee_id: int, from_date: date, to_date: date
    ) -> list[Allocation]:
        result = await self._session.execute(
            select(Allocation).where(
                Allocation.employee_id == employee_id,
                Allocation.from_date <= to_date,
                Allocation.to_date >= from_date,
            )
        )
        return list(result.scalars().all())

    async def get_by_id_with_relations(self, allocation_id: int) -> Allocation | None:
        result = await self._session.execute(
            select(Allocation)
            .where(Allocation.id == allocation_id)
            .options(
                selectinload(Allocation.employee),
                selectinload(Allocation.project).selectinload(Project.manager),
            )
        )
        return result.scalar_one_or_none()

    async def find_active_by_project(self, project_id: int) -> list[Allocation]:
        today = date.today()
        result = await self._session.execute(
            select(Allocation)
            .where(
                Allocation.project_id == project_id,
                Allocation.to_date >= today,
            )
            .options(selectinload(Allocation.employee))
            .order_by(Allocation.id)
        )
        return list(result.scalars().all())

    async def find_active_for_employee_in_week(
        self, employee_id: int, week_start: date
    ) -> list[Allocation]:
        week_end = week_start + timedelta(days=6)
        result = await self._session.execute(
            select(Allocation)
            .where(
                Allocation.employee_id == employee_id,
                Allocation.from_date <= week_end,
                Allocation.to_date >= week_start,
            )
            .options(selectinload(Allocation.project))
            .order_by(Allocation.id)
        )
        return list(result.scalars().all())

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

    async def list_active(
        self,
        *,
        employee_id: int | None,
        project_id: int | None,
        employee_name: str | None,
        project_name: str | None,
        limit: int,
        offset: int,
    ) -> list[Allocation]:
        query = self._active_query(
            employee_id=employee_id,
            project_id=project_id,
            employee_name=employee_name,
            project_name=project_name,
        )
        query = (
            query.options(
                selectinload(Allocation.employee),
                selectinload(Allocation.project),
            )
            .order_by(Allocation.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def count_active(
        self,
        *,
        employee_id: int | None,
        project_id: int | None,
        employee_name: str | None,
        project_name: str | None,
    ) -> int:
        query = self._active_query(
            employee_id=employee_id,
            project_id=project_id,
            employee_name=employee_name,
            project_name=project_name,
        )
        count_query = select(func.count()).select_from(query.subquery())
        result = await self._session.execute(count_query)
        return int(result.scalar_one())

    def _active_query(
        self,
        *,
        employee_id: int | None,
        project_id: int | None,
        employee_name: str | None,
        project_name: str | None,
    ):
        today = date.today()
        query = select(Allocation).where(Allocation.to_date >= today)

        if employee_id is not None:
            query = query.where(Allocation.employee_id == employee_id)
        if project_id is not None:
            query = query.where(Allocation.project_id == project_id)
        if employee_name:
            query = query.join(Allocation.employee).where(
                Employee.full_name.ilike(f"%{employee_name}%")
            )
        if project_name:
            query = query.join(Allocation.project).where(
                Project.name.ilike(f"%{project_name}%")
            )

        return query

    async def save(self, allocation: Allocation) -> Allocation:
        return await self.add(allocation)
