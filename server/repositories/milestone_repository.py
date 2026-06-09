from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.enums import MilestoneStatus
from server.models.milestone import Milestone
from server.repositories.base_repository import BaseRepository


class MilestoneRepository(BaseRepository[Milestone]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Milestone)

    async def find_by_project_id(self, project_id: int) -> list[Milestone]:
        result = await self._session.execute(
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.sort_order, Milestone.id)
        )
        return list(result.scalars().all())

    async def sum_done_story_points(self, project_id: int) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(Milestone.story_points), 0)).where(
                Milestone.project_id == project_id,
                Milestone.status == MilestoneStatus.DONE,
            )
        )
        return int(result.scalar_one())

    async def max_sort_order(self, project_id: int) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(Milestone.sort_order), 0)).where(
                Milestone.project_id == project_id
            )
        )
        return int(result.scalar_one())

    async def save(self, milestone: Milestone) -> Milestone:
        return await self.add(milestone)
