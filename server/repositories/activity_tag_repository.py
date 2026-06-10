from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.activity_tag import ActivityTag
from server.repositories.base_repository import BaseRepository


class ActivityTagRepository(BaseRepository[ActivityTag]):
    OTHER_TAG_NAME = "Other"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ActivityTag)

    async def list_predefined_ordered(self) -> list[ActivityTag]:
        result = await self._session.execute(
            select(ActivityTag)
            .where(ActivityTag.is_predefined.is_(True))
            .order_by(ActivityTag.display_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, tag_id: int) -> ActivityTag | None:
        return await super().get_by_id(tag_id)
