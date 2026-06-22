from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.timesheet_entry import TimesheetEntry
from server.models.timesheet_entry_tag import TimesheetEntryTag
from server.repositories.base_repository import BaseRepository


class TimesheetEntryRepository(BaseRepository[TimesheetEntry]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TimesheetEntry)

    async def save(self, entry: TimesheetEntry) -> TimesheetEntry:
        return await self.add(entry)

    async def delete_by_timesheet_id(self, timesheet_id: int) -> None:
        await self._session.execute(
            delete(TimesheetEntry).where(TimesheetEntry.timesheet_id == timesheet_id)
        )
        await self._session.flush()

    async def list_by_timesheet_id(self, timesheet_id: int) -> list[TimesheetEntry]:
        result = await self._session.execute(
            select(TimesheetEntry)
            .where(TimesheetEntry.timesheet_id == timesheet_id)
            .options(
                selectinload(TimesheetEntry.project),
                selectinload(TimesheetEntry.tags).selectinload(
                    TimesheetEntryTag.activity_tag
                ),
            )
            .order_by(TimesheetEntry.id)
        )
        return list(result.scalars().unique().all())
