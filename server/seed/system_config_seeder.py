from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.enums import LlmProvider
from server.models.system_config import SystemConfig
from server.seed.base_seeder import BaseSeeder


class SystemConfigSeeder(BaseSeeder):
    async def run(self, session: AsyncSession) -> None:
        result = await session.execute(select(SystemConfig).where(SystemConfig.id == 1))
        if result.scalar_one_or_none() is not None:
            return

        session.add(
            SystemConfig(
                id=1,
                llm_provider=LlmProvider.GEMINI,
                llm_api_key="",
                scheduler_interval_hours=4,
                max_weekly_hours=40,
            )
        )
        await session.flush()
