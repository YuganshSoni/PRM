from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.notification_log import NotificationLog
from server.repositories.base_repository import BaseRepository


class NotificationLogRepository(BaseRepository[NotificationLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NotificationLog)

    async def exists(
        self, notification_type: str, dedupe_key: str, recipient_email: str
    ) -> bool:
        result = await self._session.execute(
            select(NotificationLog.id).where(
                NotificationLog.notification_type == notification_type,
                NotificationLog.dedupe_key == dedupe_key,
                NotificationLog.recipient_email == recipient_email,
            )
        )
        return result.scalar_one_or_none() is not None

    async def save(self, entry: NotificationLog) -> NotificationLog:
        return await self.add(entry)
