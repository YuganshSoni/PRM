from sqlalchemy.ext.asyncio import AsyncSession

from server.models.timesheet_entry_tag import TimesheetEntryTag
from server.repositories.base_repository import BaseRepository


class TimesheetEntryTagRepository(BaseRepository[TimesheetEntryTag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TimesheetEntryTag)

    async def save_all(self, tags: list[TimesheetEntryTag]) -> list[TimesheetEntryTag]:
        saved: list[TimesheetEntryTag] = []
        for tag in tags:
            saved.append(await self.add(tag))
        return saved
