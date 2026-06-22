from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.allocation import Allocation
from server.models.project import Project
from server.models.resource import Resource
from server.models.user import User
from server.repositories.base_repository import BaseRepository


class AllocationRepository(BaseRepository[Allocation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Allocation)

    async def find_active_by_team(self, manager_resource_id: int) -> list[Allocation]:
        today = date.today()
        result = await self._session.execute(
            select(Allocation)
            .join(Resource, Allocation.resource_id == Resource.id)
            .where(
                Resource.manager_id == manager_resource_id,
                Allocation.to_date >= today,
            )
            .options(
                selectinload(Allocation.resource).selectinload(Resource.user),
                selectinload(Allocation.project),
            )
            .order_by(Allocation.resource_id, Allocation.id)
        )
        return list(result.scalars().unique().all())

    async def find_overlapping(
        self, resource_id: int, from_date: date, to_date: date
    ) -> list[Allocation]:
        result = await self._session.execute(
            select(Allocation).where(
                Allocation.resource_id == resource_id,
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
                selectinload(Allocation.resource).selectinload(Resource.user),
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
                Allocation.from_date <= today,
                Allocation.to_date >= today,
            )
            .options(
                selectinload(Allocation.resource).selectinload(Resource.user),
            )
            .order_by(Allocation.id)
        )
        return list(result.scalars().all())

    async def find_active_for_resource_in_week(
        self, resource_id: int, week_start: date
    ) -> list[Allocation]:
        week_end = week_start + timedelta(days=6)
        result = await self._session.execute(
            select(Allocation)
            .where(
                Allocation.resource_id == resource_id,
                Allocation.from_date <= week_end,
                Allocation.to_date >= week_start,
            )
            .options(selectinload(Allocation.project))
            .order_by(Allocation.id)
        )
        return list(result.scalars().all())

    async def find_on_manager_projects_in_week(
        self, manager_resource_id: int, week_start: date
    ) -> list[Allocation]:
        week_end = week_start + timedelta(days=6)
        result = await self._session.execute(
            select(Allocation)
            .join(Project, Allocation.project_id == Project.id)
            .where(
                Project.manager_id == manager_resource_id,
                Allocation.from_date <= week_end,
                Allocation.to_date >= week_start,
            )
            .options(
                selectinload(Allocation.resource).selectinload(Resource.user),
                selectinload(Allocation.project),
            )
            .order_by(Allocation.resource_id, Allocation.project_id)
        )
        return list(result.scalars().all())

    async def find_all_active(self) -> list[Allocation]:
        today = date.today()
        result = await self._session.execute(
            select(Allocation).where(Allocation.to_date >= today)
        )
        return list(result.scalars().all())

    async def find_overlapping_week(self, week_start: date) -> list[Allocation]:
        week_end = week_start + timedelta(days=6)
        result = await self._session.execute(
            select(Allocation).where(
                Allocation.from_date <= week_end,
                Allocation.to_date >= week_start,
            )
        )
        return list(result.scalars().all())

    async def find_active_for_project_in_week(
        self, project_id: int, week_start: date
    ) -> list[Allocation]:
        week_end = week_start + timedelta(days=6)
        result = await self._session.execute(
            select(Allocation)
            .where(
                Allocation.project_id == project_id,
                Allocation.from_date <= week_end,
                Allocation.to_date >= week_start,
            )
            .options(selectinload(Allocation.resource).selectinload(Resource.user))
            .order_by(Allocation.id)
        )
        return list(result.scalars().all())

    async def find_active_by_resource(self, resource_id: int) -> list[Allocation]:
        today = date.today()
        result = await self._session.execute(
            select(Allocation)
            .where(
                Allocation.resource_id == resource_id,
                Allocation.to_date >= today,
            )
            .options(selectinload(Allocation.project))
            .order_by(Allocation.id)
        )
        return list(result.scalars().all())

    async def list_active(
        self,
        *,
        resource_id: int | None,
        project_id: int | None,
        resource_name: str | None,
        project_name: str | None,
        limit: int,
        offset: int,
    ) -> list[Allocation]:
        query = self._active_query(
            resource_id=resource_id,
            project_id=project_id,
            resource_name=resource_name,
            project_name=project_name,
        )
        query = (
            query.options(
                selectinload(Allocation.resource).selectinload(Resource.user),
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
        resource_id: int | None,
        project_id: int | None,
        resource_name: str | None,
        project_name: str | None,
    ) -> int:
        query = self._active_query(
            resource_id=resource_id,
            project_id=project_id,
            resource_name=resource_name,
            project_name=project_name,
        )
        count_query = select(func.count()).select_from(query.subquery())
        result = await self._session.execute(count_query)
        return int(result.scalar_one())

    def _active_query(
        self,
        *,
        resource_id: int | None,
        project_id: int | None,
        resource_name: str | None,
        project_name: str | None,
    ):
        today = date.today()
        query = select(Allocation).where(Allocation.to_date >= today)

        if resource_id is not None:
            query = query.where(Allocation.resource_id == resource_id)
        if project_id is not None:
            query = query.where(Allocation.project_id == project_id)
        if resource_name:
            query = (
                query.join(Allocation.resource)
                .join(Resource.user)
                .where(User.full_name.ilike(f"%{resource_name}%"))
            )
        if project_name:
            query = query.join(Allocation.project).where(
                Project.name.ilike(f"%{project_name}%")
            )

        return query

    async def save(self, allocation: Allocation) -> Allocation:
        return await self.add(allocation)
