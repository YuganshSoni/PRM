from datetime import date, timedelta

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.activity_tag import ActivityTag
from server.models.timesheet import Timesheet
from server.models.timesheet_entry import TimesheetEntry
from server.models.timesheet_entry_tag import TimesheetEntryTag
from server.repositories.base_repository import BaseRepository


class TimesheetRepository(BaseRepository[Timesheet]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Timesheet)

    async def find_recent_activity_tags(
        self, employee_id: int, *, weeks: int = 4
    ) -> list[str]:
        cutoff = date.today() - timedelta(weeks=weeks)
        display_name = case(
            (TimesheetEntryTag.custom_label.isnot(None), TimesheetEntryTag.custom_label),
            else_=ActivityTag.name,
        )
        result = await self._session.execute(
            select(display_name)
            .select_from(TimesheetEntryTag)
            .join(
                TimesheetEntry,
                TimesheetEntryTag.timesheet_entry_id == TimesheetEntry.id,
            )
            .join(Timesheet, TimesheetEntry.timesheet_id == Timesheet.id)
            .join(ActivityTag, TimesheetEntryTag.activity_tag_id == ActivityTag.id)
            .where(
                Timesheet.employee_id == employee_id,
                Timesheet.week_start >= cutoff,
                Timesheet.submitted_at.isnot(None),
            )
            .distinct()
            .order_by(display_name)
        )
        return [row[0] for row in result.all() if row[0]]
