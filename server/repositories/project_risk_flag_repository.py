from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.project_risk_flag import ProjectRiskFlag
from server.repositories.base_repository import BaseRepository


class ProjectRiskFlagRepository(BaseRepository[ProjectRiskFlag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectRiskFlag)

    async def delete_by_health_id(self, health_id: int) -> None:
        await self._session.execute(
            delete(ProjectRiskFlag).where(
                ProjectRiskFlag.project_health_id == health_id
            )
        )

    async def find_by_health_id(self, health_id: int) -> list[ProjectRiskFlag]:
        result = await self._session.execute(
            select(ProjectRiskFlag)
            .where(ProjectRiskFlag.project_health_id == health_id)
            .order_by(ProjectRiskFlag.sort_order, ProjectRiskFlag.id)
        )
        return list(result.scalars().all())

    async def find_by_health_ids(
        self, health_ids: list[int]
    ) -> dict[int, list[ProjectRiskFlag]]:
        if not health_ids:
            return {}
        result = await self._session.execute(
            select(ProjectRiskFlag)
            .where(ProjectRiskFlag.project_health_id.in_(health_ids))
            .order_by(ProjectRiskFlag.sort_order, ProjectRiskFlag.id)
        )
        grouped: dict[int, list[ProjectRiskFlag]] = {hid: [] for hid in health_ids}
        for flag in result.scalars().all():
            grouped.setdefault(flag.project_health_id, []).append(flag)
        return grouped

    async def save_all(self, flags: list[ProjectRiskFlag]) -> None:
        for flag in flags:
            self._session.add(flag)
