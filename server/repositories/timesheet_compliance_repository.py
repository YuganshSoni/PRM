from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.timesheet_compliance_record import TimesheetComplianceRecord
from server.repositories.base_repository import BaseRepository


class TimesheetComplianceRepository(BaseRepository[TimesheetComplianceRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TimesheetComplianceRecord)

    async def find_by_resource_and_week(
        self, resource_id: int, week_start: date
    ) -> TimesheetComplianceRecord | None:
        result = await self._session.execute(
            select(TimesheetComplianceRecord).where(
                TimesheetComplianceRecord.resource_id == resource_id,
                TimesheetComplianceRecord.week_start == week_start,
            )
        )
        return result.scalar_one_or_none()

    async def find_frozen_by_resource(
        self, resource_id: int
    ) -> TimesheetComplianceRecord | None:
        result = await self._session.execute(
            select(TimesheetComplianceRecord).where(
                TimesheetComplianceRecord.resource_id == resource_id,
                TimesheetComplianceRecord.status == "FROZEN",
            )
        )
        return result.scalar_one_or_none()

    async def find_frozen_for_manager(
        self, manager_resource_id: int
    ) -> list[TimesheetComplianceRecord]:
        from server.models.resource import Resource

        result = await self._session.execute(
            select(TimesheetComplianceRecord)
            .join(Resource, TimesheetComplianceRecord.resource_id == Resource.id)
            .where(
                Resource.manager_id == manager_resource_id,
                TimesheetComplianceRecord.status == "FROZEN",
            )
            .order_by(TimesheetComplianceRecord.week_start.desc())
        )
        return list(result.scalars().all())

    async def save(
        self, record: TimesheetComplianceRecord
    ) -> TimesheetComplianceRecord:
        return await self.add(record)
