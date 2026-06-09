from sqlalchemy.ext.asyncio import AsyncSession

from server.models.system_config import SystemConfig
from server.repositories.base_repository import BaseRepository


class SystemConfigRepository(BaseRepository[SystemConfig]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SystemConfig)

    async def get(self) -> SystemConfig | None:
        return await self.get_by_id(1)

    async def save(self, config: SystemConfig) -> SystemConfig:
        return await self.add(config)
