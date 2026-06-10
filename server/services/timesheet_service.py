from datetime import date, datetime, timezone
from decimal import Decimal

from server.core.exceptions import (
    DuplicateTimesheetError,
    EmployeeProfileNotFoundError,
    HoursExceededError,
    InvalidActivityTagError,
    NoTimesheetEntriesError,
    NotAllocatedToProjectError,
    OtherTagRequiresLabelError,
    SystemConfigNotFoundError,
    TimesheetNotFoundError,
    TotalHoursExceededError,
)
from server.core.week_utils import WeekCalculator
from server.models.enums import TimesheetStatus
from server.models.timesheet import Timesheet
from server.models.timesheet_entry import TimesheetEntry
from server.models.timesheet_entry_tag import TimesheetEntryTag
from server.models.user import User
from server.repositories.activity_tag_repository import ActivityTagRepository
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.employee_repository import EmployeeRepository
from server.repositories.system_config_repository import SystemConfigRepository
from server.repositories.timesheet_entry_repository import TimesheetEntryRepository
from server.repositories.timesheet_entry_tag_repository import TimesheetEntryTagRepository
from server.repositories.timesheet_repository import TimesheetRepository
from server.schemas.requests.timesheet import (
    SubmitTimesheetRequest,
    TimesheetEntryRequest,
    TimesheetEntryTagRequest,
)
from server.schemas.responses.timesheet import (
    MissedReminderResponse,
    TimesheetDetailResponse,
    TimesheetEntryDetailResponse,
    TimesheetSummaryResponse,
)


class TimesheetService:
    def __init__(
        self,
        timesheet_repository: TimesheetRepository,
        timesheet_entry_repository: TimesheetEntryRepository,
        timesheet_entry_tag_repository: TimesheetEntryTagRepository,
        activity_tag_repository: ActivityTagRepository,
        allocation_repository: AllocationRepository,
        employee_repository: EmployeeRepository,
        system_config_repository: SystemConfigRepository,
    ) -> None:
        self._timesheet_repository = timesheet_repository
        self._timesheet_entry_repository = timesheet_entry_repository
        self._timesheet_entry_tag_repository = timesheet_entry_tag_repository
        self._activity_tag_repository = activity_tag_repository
        self._allocation_repository = allocation_repository
        self._employee_repository = employee_repository
        self._system_config_repository = system_config_repository

    async def submit_timesheet(
        self, dto: SubmitTimesheetRequest, user: User
    ) -> Timesheet:
        if not dto.entries:
            raise NoTimesheetEntriesError("At least one timesheet entry is required")

        employee_id = await self._resolve_employee_id(user)
        today = date.today()

        WeekCalculator.validate_monday(dto.week_start)
        WeekCalculator.ensure_not_future(dto.week_start, today)

        existing = await self._timesheet_repository.find_by_employee_and_week(
            employee_id, dto.week_start
        )
        if existing is not None and existing.status == TimesheetStatus.SUBMITTED:
            raise DuplicateTimesheetError(
                "Timesheet already submitted for this week"
            )

        allocations = await self._allocation_repository.find_active_for_employee_in_week(
            employee_id, dto.week_start
        )
        allocation_by_project = {item.project_id: item for item in allocations}

        config = await self._system_config_repository.get()
        if config is None:
            raise SystemConfigNotFoundError("System configuration not found")
        max_weekly_hours = config.max_weekly_hours

        self.validate_hours(dto.entries, allocation_by_project, max_weekly_hours)
        await self._validate_tags(dto.entries)

        total_hours = sum((entry.hours for entry in dto.entries), Decimal(0))
        now = datetime.now(timezone.utc)

        if existing is not None:
            timesheet = existing
            timesheet.status = TimesheetStatus.SUBMITTED
            timesheet.total_hours = total_hours
            timesheet.submitted_at = now
            await self._timesheet_repository.save(timesheet)
            await self._timesheet_entry_repository.delete_by_timesheet_id(
                timesheet.id
            )
        else:
            timesheet = Timesheet(
                employee_id=employee_id,
                week_start=dto.week_start,
                status=TimesheetStatus.SUBMITTED,
                total_hours=total_hours,
                submitted_at=now,
            )
            timesheet = await self._timesheet_repository.save(timesheet)

        for entry_dto in dto.entries:
            entry = TimesheetEntry(
                timesheet_id=timesheet.id,
                project_id=entry_dto.project_id,
                hours=entry_dto.hours,
            )
            saved_entry = await self._timesheet_entry_repository.save(entry)
            tag_rows = await self._build_entry_tags(entry_dto.tags, saved_entry.id)
            await self._timesheet_entry_tag_repository.save_all(tag_rows)

        return timesheet

    async def list_my_timesheets(self, user: User) -> list[TimesheetSummaryResponse]:
        employee_id = await self._resolve_employee_id(user)
        timesheets = await self._timesheet_repository.list_by_employee(employee_id)
        return [
            TimesheetSummaryResponse(
                id=item.id,
                week_start=item.week_start,
                total_hours=item.total_hours,
                status=item.status,
            )
            for item in timesheets
        ]

    async def get_timesheet_detail(
        self, timesheet_id: int, user: User
    ) -> TimesheetDetailResponse:
        employee_id = await self._resolve_employee_id(user)
        timesheet = await self._timesheet_repository.get_by_id_with_entries(
            timesheet_id
        )
        if timesheet is None or timesheet.employee_id != employee_id:
            raise TimesheetNotFoundError("Timesheet not found")

        entries = [
            TimesheetEntryDetailResponse(
                project_name=entry.project.name,
                hours=entry.hours,
                activity_tags=self._format_entry_tags(entry),
            )
            for entry in timesheet.entries
        ]
        return TimesheetDetailResponse(
            id=timesheet.id,
            week_start=timesheet.week_start,
            status=timesheet.status,
            total_hours=timesheet.total_hours,
            entries=entries,
        )

    async def get_missed_reminder(self, user: User) -> MissedReminderResponse:
        employee_id = await self._resolve_employee_id(user)
        prior_week = WeekCalculator.prior_week_monday(date.today())
        timesheet = await self._timesheet_repository.find_by_employee_and_week(
            employee_id, prior_week
        )

        if timesheet is None or timesheet.status == TimesheetStatus.MISSED:
            return MissedReminderResponse(
                show_reminder=True,
                week_start=prior_week,
                message=(
                    f"Reminder: Timesheet for week {prior_week.isoformat()} "
                    "has not been submitted."
                ),
            )

        return MissedReminderResponse(show_reminder=False)

    def validate_hours(
        self,
        entries: list[TimesheetEntryRequest],
        allocation_by_project: dict[int, object],
        max_weekly_hours: int,
    ) -> None:
        total = Decimal(0)
        max_weekly = Decimal(max_weekly_hours)

        for entry in entries:
            allocation = allocation_by_project.get(entry.project_id)
            if allocation is None:
                raise NotAllocatedToProjectError(
                    f"Not allocated to project {entry.project_id} for this week"
                )

            project_max = (
                Decimal(allocation.utilisation_percent) / Decimal(100) * max_weekly
            )
            if entry.hours > project_max:
                raise HoursExceededError(
                    f"Hours for project {entry.project_id} exceed maximum "
                    f"of {project_max}"
                )
            total += entry.hours

        if total > max_weekly:
            raise TotalHoursExceededError(
                f"Total hours {total} exceed weekly maximum of {max_weekly_hours}"
            )

    async def _validate_tags(self, entries: list[TimesheetEntryRequest]) -> None:
        predefined = await self._activity_tag_repository.list_predefined_ordered()
        tag_by_id = {tag.id: tag for tag in predefined}
        other_tag = next(
            (
                tag
                for tag in predefined
                if tag.name == ActivityTagRepository.OTHER_TAG_NAME
            ),
            None,
        )

        for entry in entries:
            for tag_request in entry.tags:
                tag = tag_by_id.get(tag_request.activity_tag_id)
                if tag is None:
                    raise InvalidActivityTagError(
                        f"Unknown activity tag {tag_request.activity_tag_id}"
                    )
                if (
                    other_tag is not None
                    and tag.id == other_tag.id
                    and not tag_request.custom_label
                ):
                    raise OtherTagRequiresLabelError(
                        "Custom label is required when selecting Other"
                    )

    async def _build_entry_tags(
        self,
        tags: list[TimesheetEntryTagRequest],
        entry_id: int,
    ) -> list[TimesheetEntryTag]:
        predefined = await self._activity_tag_repository.list_predefined_ordered()
        tag_by_id = {tag.id: tag for tag in predefined}
        other_tag = next(
            (
                tag
                for tag in predefined
                if tag.name == ActivityTagRepository.OTHER_TAG_NAME
            ),
            None,
        )

        rows: list[TimesheetEntryTag] = []
        for tag_request in tags:
            tag = tag_by_id[tag_request.activity_tag_id]
            custom_label = None
            if other_tag is not None and tag.id == other_tag.id:
                custom_label = tag_request.custom_label
            rows.append(
                TimesheetEntryTag(
                    timesheet_entry_id=entry_id,
                    activity_tag_id=tag.id,
                    custom_label=custom_label,
                )
            )
        return rows

    async def _resolve_employee_id(self, user: User) -> int:
        employee = await self._employee_repository.find_by_user_id(user.id)
        if employee is None:
            raise EmployeeProfileNotFoundError(
                "Employee user does not have an employee profile"
            )
        return employee.id

    def _format_entry_tags(self, entry: TimesheetEntry) -> list[str]:
        labels: list[str] = []
        for tag_link in entry.tags:
            if tag_link.custom_label:
                labels.append(tag_link.custom_label)
            else:
                labels.append(tag_link.activity_tag.name)
        return labels
