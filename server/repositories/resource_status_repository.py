from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.resource_status import ResourceStatus
from server.repositories.base_repository import BaseRepository


class ResourceStatusRepository(BaseRepository[ResourceStatus]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ResourceStatus)

    async def find_by_name(self, name: str) -> ResourceStatus | None:
        result = await self._session.execute(
            select(ResourceStatus).where(ResourceStatus.name == name)
        )
        return result.scalar_one_or_none()
