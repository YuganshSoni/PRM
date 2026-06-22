from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from server.core.exceptions import (
    DuplicateTimesheetError,
    EmployeeProfileNotFoundError,
    HoursExceededError,
    InvalidActivityTagError,
    ManagerProfileNotFoundError,
    NoTimesheetEntriesError,
    NotAllocatedToProjectError,
    OtherTagRequiresLabelError,
    SystemConfigNotFoundError,
    TimesheetNotFoundError,
    TimesheetSubmissionFrozenError,
    TotalHoursExceededError,
)
from server.core.user_role import user_role_enum
from server.core.week_utils import WeekCalculator
from server.models.allocation import Allocation
from server.models.enums import TimesheetStatus, UserRole
from server.models.timesheet import Timesheet
from server.models.timesheet_entry import TimesheetEntry
from server.models.timesheet_entry_tag import TimesheetEntryTag
from server.models.user import User
from server.repositories.activity_tag_repository import ActivityTagRepository
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.resource_repository import ResourceRepository
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
    TeamTimesheetListResponse,
    TeamTimesheetRowResponse,
    TimesheetDetailResponse,
    TimesheetEntryDetailResponse,
    TimesheetSummaryResponse,
)
from server.services.scheduler_results import MissedMarkResult, ComplianceRunResult


class TimesheetService:
    MISSED_WEEK_LOOKBACK = 3

    def __init__(
        self,
        timesheet_repository: TimesheetRepository,
        timesheet_entry_repository: TimesheetEntryRepository,
        timesheet_entry_tag_repository: TimesheetEntryTagRepository,
        activity_tag_repository: ActivityTagRepository,
        allocation_repository: AllocationRepository,
        resource_repository: ResourceRepository,
        system_config_repository: SystemConfigRepository,
        compliance_service=None,
    ) -> None:
        self._timesheet_repository = timesheet_repository
        self._timesheet_entry_repository = timesheet_entry_repository
        self._timesheet_entry_tag_repository = timesheet_entry_tag_repository
        self._activity_tag_repository = activity_tag_repository
        self._allocation_repository = allocation_repository
        self._resource_repository = resource_repository
        self._system_config_repository = system_config_repository
        self._compliance_service = compliance_service

    async def submit_timesheet(
        self, dto: SubmitTimesheetRequest, user: User
    ) -> Timesheet:
        if not dto.entries:
            raise NoTimesheetEntriesError("At least one timesheet entry is required")

        resource_id = await self._resolve_resource_id(user)
        if self._compliance_service is not None:
            if await self._compliance_service.is_submission_frozen(resource_id):
                raise TimesheetSubmissionFrozenError(
                    "Timesheet submission is frozen. Contact your manager."
                )
        today = date.today()

        WeekCalculator.validate_monday(dto.week_start)
        WeekCalculator.ensure_not_future(dto.week_start, today)

        existing = await self._timesheet_repository.find_by_resource_and_week(
            resource_id, dto.week_start
        )
        if existing is not None and existing.status == TimesheetStatus.SUBMITTED:
            raise DuplicateTimesheetError(
                "Timesheet already submitted for this week"
            )

        allocations = await self._allocation_repository.find_active_for_resource_in_week(
            resource_id, dto.week_start
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
                resource_id=resource_id,
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

        if self._compliance_service is not None:
            await self._compliance_service.mark_submitted(
                resource_id, dto.week_start
            )

        return timesheet

    async def list_my_timesheets(self, user: User) -> list[TimesheetSummaryResponse]:
        resource_id = await self._resolve_resource_id(user)
        timesheets = await self._timesheet_repository.list_by_resource(resource_id)
        return [
            TimesheetSummaryResponse(
                id=item.id,
                week_start=item.week_start,
                total_hours=item.total_hours,
                status=item.status,
            )
            for item in timesheets
        ]

    async def list_team_timesheets(
        self, user: User, week_start: date
    ) -> TeamTimesheetListResponse:
        manager_resource_id = await self._resolve_manager_resource_id(user)
        today = date.today()

        WeekCalculator.validate_monday(week_start)
        WeekCalculator.ensure_not_future(week_start, today)

        allocations = (
            await self._allocation_repository.find_on_manager_projects_in_week(
                manager_resource_id, week_start
            )
        )
        if not allocations:
            return TeamTimesheetListResponse(week_start=week_start, items=[])

        resource_ids = list({allocation.resource_id for allocation in allocations})
        timesheets = await self._timesheet_repository.find_by_resources_and_week(
            resource_ids, week_start
        )
        timesheet_by_resource = {item.resource_id: item for item in timesheets}
        entry_by_resource_project = self._entry_hours_by_resource_project(timesheets)

        rows = [
            self._build_team_row(
                allocation,
                timesheet_by_resource,
                entry_by_resource_project,
            )
            for allocation in allocations
        ]
        rows.sort(key=lambda row: (row.resource_name.lower(), row.project_name.lower()))
        return TeamTimesheetListResponse(week_start=week_start, items=rows)

    async def get_timesheet_detail(
        self, timesheet_id: int, user: User
    ) -> TimesheetDetailResponse:
        timesheet = await self._timesheet_repository.get_by_id_with_entries(
            timesheet_id
        )
        if timesheet is None:
            raise TimesheetNotFoundError("Timesheet not found")

        role = user_role_enum(user)
        if role == UserRole.RESOURCE:
            resource_id = await self._resolve_resource_id(user)
            if timesheet.resource_id != resource_id:
                raise TimesheetNotFoundError("Timesheet not found")
        elif role == UserRole.MANAGER:
            manager_resource_id = await self._resolve_manager_resource_id(user)
            await self._ensure_manager_can_view_timesheet(
                timesheet, manager_resource_id
            )
        else:
            raise TimesheetNotFoundError("Timesheet not found")

        return self._to_detail_response(timesheet)

    async def get_missed_reminder(self, user: User) -> MissedReminderResponse:
        resource_id = await self._resolve_resource_id(user)
        prior_week = WeekCalculator.prior_week_monday(date.today())
        timesheet = await self._timesheet_repository.find_by_resource_and_week(
            resource_id, prior_week
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

    async def mark_missed_timesheets(self) -> MissedMarkResult:
        today = date.today()
        created = updated = skipped = 0

        for week_start in self._weeks_to_check(today):
            allocations = await self._allocation_repository.find_overlapping_week(
                week_start
            )
            resource_ids = {allocation.resource_id for allocation in allocations}

            for resource_id in resource_ids:
                existing = await self._timesheet_repository.find_by_resource_and_week(
                    resource_id, week_start
                )
                if existing is not None and existing.status == TimesheetStatus.SUBMITTED:
                    skipped += 1
                    continue

                if existing is None:
                    await self._timesheet_repository.save(
                        Timesheet(
                            resource_id=resource_id,
                            week_start=week_start,
                            status=TimesheetStatus.MISSED,
                            total_hours=Decimal(0),
                        )
                    )
                    created += 1
                else:
                    existing.status = TimesheetStatus.MISSED
                    existing.total_hours = Decimal(0)
                    existing.submitted_at = None
                    await self._timesheet_repository.save(existing)
                    updated += 1

        return MissedMarkResult(
            created=created,
            updated=updated,
            skipped=skipped,
        )

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

    @staticmethod
    def _weeks_to_check(today: date) -> list[date]:
        current_week = WeekCalculator.current_week_monday(today)
        prior_week = WeekCalculator.prior_week_monday(today)
        weeks = [prior_week]
        for offset in range(1, TimesheetService.MISSED_WEEK_LOOKBACK + 1):
            weeks.append(prior_week - timedelta(days=7 * offset))
        return [week for week in weeks if week < current_week]

    async def _resolve_resource_id(self, user: User) -> int:
        resource = await self._resource_repository.find_by_user_id(user.id)
        if resource is None:
            raise EmployeeProfileNotFoundError(
                "Resource user does not have an resource profile"
            )
        return resource.id

    async def _resolve_manager_resource_id(self, user: User) -> int:
        manager_resource = await self._resource_repository.find_by_user_id(user.id)
        if manager_resource is None:
            raise ManagerProfileNotFoundError(
                "Manager user does not have an resource profile"
            )
        return manager_resource.id

    async def _ensure_manager_can_view_timesheet(
        self, timesheet: Timesheet, manager_resource_id: int
    ) -> None:
        allocations = (
            await self._allocation_repository.find_on_manager_projects_in_week(
                manager_resource_id, timesheet.week_start
            )
        )
        allowed_resource_ids = {allocation.resource_id for allocation in allocations}
        if timesheet.resource_id not in allowed_resource_ids:
            raise TimesheetNotFoundError("Timesheet not found")

    @staticmethod
    def _entry_hours_by_resource_project(
        timesheets: list[Timesheet],
    ) -> dict[tuple[int, int], Decimal]:
        lookup: dict[tuple[int, int], Decimal] = {}
        for timesheet in timesheets:
            for entry in timesheet.entries:
                lookup[(timesheet.resource_id, entry.project_id)] = entry.hours
        return lookup

    @staticmethod
    def _build_team_row(
        allocation: Allocation,
        timesheet_by_resource: dict[int, Timesheet],
        entry_by_resource_project: dict[tuple[int, int], Decimal],
    ) -> TeamTimesheetRowResponse:
        resource = allocation.resource
        project = allocation.project
        timesheet = timesheet_by_resource.get(allocation.resource_id)
        resource_name = TimesheetService._resource_display_name(resource)

        if timesheet is None or timesheet.status == TimesheetStatus.MISSED:
            return TeamTimesheetRowResponse(
                resource_id=allocation.resource_id,
                resource_name=resource_name,
                project_id=project.id,
                project_name=project.name,
                hours=Decimal(0),
                status=TimesheetStatus.MISSED,
                timesheet_id=timesheet.id if timesheet else None,
            )

        hours = entry_by_resource_project.get(
            (allocation.resource_id, project.id), Decimal(0)
        )
        return TeamTimesheetRowResponse(
            resource_id=allocation.resource_id,
            resource_name=resource_name,
            project_id=project.id,
            project_name=project.name,
            hours=hours,
            status=TimesheetStatus.SUBMITTED,
            timesheet_id=timesheet.id,
        )

    @staticmethod
    def _resource_display_name(resource: object) -> str:
        user = getattr(resource, "user", None)
        if user is not None:
            return user.full_name
        return "Resource"

    def _to_detail_response(self, timesheet: Timesheet) -> TimesheetDetailResponse:
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

    def _format_entry_tags(self, entry: TimesheetEntry) -> list[str]:
        labels: list[str] = []
        for tag_link in entry.tags:
            if tag_link.custom_label:
                labels.append(tag_link.custom_label)
            else:
                labels.append(tag_link.activity_tag.name)
        return labels
