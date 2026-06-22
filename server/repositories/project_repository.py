from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.enums import ProjectStatus
from server.models.project import Project
from server.models.resource import Resource
from server.repositories.base_repository import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def get_by_id_with_manager(self, project_id: int) -> Project | None:
        result = await self._session.execute(
            select(Project)
            .options(
                selectinload(Project.manager).selectinload(Resource.user),
            )
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        *,
        status: ProjectStatus | None,
        limit: int,
        offset: int,
    ) -> list[Project]:
        query = (
            select(Project)
            .options(
                selectinload(Project.manager).selectinload(Resource.user),
            )
            .order_by(Project.id)
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            query = query.where(Project.status == status)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_projects(self, *, status: ProjectStatus | None = None) -> int:
        query = select(func.count()).select_from(Project)
        if status is not None:
            query = query.where(Project.status == status)
        result = await self._session.execute(query)
        return int(result.scalar_one())

    async def find_by_manager_id(self, manager_id: int) -> list[Project]:
        result = await self._session.execute(
            select(Project)
            .where(Project.manager_id == manager_id)
            .order_by(Project.id)
        )
        return list(result.scalars().all())

    async def find_active_projects(self) -> list[Project]:
        result = await self._session.execute(
            select(Project)
            .where(Project.status == ProjectStatus.ACTIVE)
            .order_by(Project.id)
        )
        return list(result.scalars().all())

    async def save(self, project: Project) -> Project:
        return await self.add(project)
