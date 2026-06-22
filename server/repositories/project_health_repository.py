from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.project_health import ProjectHealth
from server.repositories.base_repository import BaseRepository


class ProjectHealthRepository(BaseRepository[ProjectHealth]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectHealth)

    async def find_by_project_id(self, project_id: int) -> ProjectHealth | None:
        result = await self._session.execute(
            select(ProjectHealth).where(ProjectHealth.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def find_by_project_ids(
        self, project_ids: list[int]
    ) -> dict[int, ProjectHealth]:
        if not project_ids:
            return {}
        result = await self._session.execute(
            select(ProjectHealth).where(ProjectHealth.project_id.in_(project_ids))
        )
        return {health.project_id: health for health in result.scalars().all()}

    async def save(self, health: ProjectHealth) -> ProjectHealth:
        return await self.add(health)
