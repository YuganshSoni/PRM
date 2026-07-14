from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.core.exceptions import (
    DuplicateTimesheetError,
    DuplicateTimesheetProjectError,
    EmployeeProfileNotFoundError,
    HoursExceededError,
    InvalidActivityTagError,
    NoTimesheetEntriesError,
    NotAllocatedToProjectError,
    OtherTagRequiresLabelError,
    TimesheetNotFoundError,
    TimesheetSubmissionFrozenError,
    TotalHoursExceededError,
)
from server.models.enums import TimesheetStatus
from server.repositories.activity_tag_repository import ActivityTagRepository
from server.schemas.requests.timesheet import (
    SubmitTimesheetRequest,
    TimesheetEntryRequest,
    TimesheetEntryTagRequest,
)
from server.services.timesheet_service import TimesheetService


@pytest.fixture
def timesheet_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def entry_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def entry_tag_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def activity_tag_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def allocation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def resource_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def system_config_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def compliance_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    timesheet_repo,
    entry_repo,
    entry_tag_repo,
    activity_tag_repo,
    allocation_repo,
    resource_repo,
    system_config_repo,
    compliance_service,
) -> TimesheetService:
    return TimesheetService(
        timesheet_repo,
        entry_repo,
        entry_tag_repo,
        activity_tag_repo,
        allocation_repo,
        resource_repo,
        system_config_repo,
        compliance_service=compliance_service,
    )


def _entry(
    project_id: int = 1,
    hours: str | Decimal = "8",
    tag_id: int = 1,
    custom_label: str | None = None,
) -> TimesheetEntryRequest:
    return TimesheetEntryRequest(
        project_id=project_id,
        hours=Decimal(hours),
        tags=[
            TimesheetEntryTagRequest(
                activity_tag_id=tag_id, custom_label=custom_label
            )
        ],
    )


def test_validate_hours_rejects_unallocated_project(service):
    with pytest.raises(NotAllocatedToProjectError):
        service.validate_hours([_entry(project_id=9)], {}, 40)


def test_validate_hours_rejects_duplicate_projects(service):
    with pytest.raises(DuplicateTimesheetProjectError):
        service.validate_hours(
            [_entry(project_id=1), _entry(project_id=1)],
            {1: 100},
            40,
        )


def test_validate_hours_rejects_project_over_cap(service):
    # 50% of 40h = 20h max
    with pytest.raises(HoursExceededError):
        service.validate_hours([_entry(hours="21")], {1: 50}, 40)


def test_validate_hours_rejects_total_over_weekly_max(service):
    entries = [
        _entry(project_id=1, hours="25"),
        _entry(project_id=2, hours="20"),
    ]
    with pytest.raises(TotalHoursExceededError):
        service.validate_hours(entries, {1: 100, 2: 100}, 40)


def test_validate_hours_happy_path(service):
    service.validate_hours([_entry(hours="16")], {1: 50}, 40)


@pytest.mark.asyncio
async def test_submit_requires_entries(service):
    # pydantic Field(min_length=1) prevents empty list on DTO construction;
    # exercise the service guard via MagicMock.
    dto = MagicMock()
    dto.entries = []
    with pytest.raises(NoTimesheetEntriesError):
        await service.submit_timesheet(dto, SimpleNamespace(id=1))


@pytest.mark.asyncio
async def test_submit_requires_resource_profile(service, resource_repo, compliance_service):
    compliance_service.is_submission_frozen.return_value = False
    resource_repo.find_by_user_id.return_value = None
    dto = SubmitTimesheetRequest(
        week_start=date(2026, 7, 6),
        entries=[_entry()],
    )
    with pytest.raises(EmployeeProfileNotFoundError):
        await service.submit_timesheet(dto, SimpleNamespace(id=1))


@pytest.mark.asyncio
async def test_submit_frozen_blocks(service, resource_repo, compliance_service):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    compliance_service.is_submission_frozen.return_value = True
    dto = SubmitTimesheetRequest(
        week_start=date(2026, 7, 6),
        entries=[_entry()],
    )
    with pytest.raises(TimesheetSubmissionFrozenError):
        await service.submit_timesheet(dto, SimpleNamespace(id=1))


@pytest.mark.asyncio
async def test_submit_rejects_already_submitted(
    service,
    resource_repo,
    compliance_service,
    timesheet_repo,
):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    compliance_service.is_submission_frozen.return_value = False
    timesheet_repo.find_by_resource_and_week.return_value = SimpleNamespace(
        status=TimesheetStatus.SUBMITTED
    )
    dto = SubmitTimesheetRequest(
        week_start=date(2026, 7, 6),
        entries=[_entry()],
    )
    with pytest.raises(DuplicateTimesheetError):
        await service.submit_timesheet(dto, SimpleNamespace(id=1))


@pytest.mark.asyncio
async def test_validate_tags_unknown_tag(service, activity_tag_repo):
    activity_tag_repo.list_predefined_ordered.return_value = [
        SimpleNamespace(id=1, name="Dev"),
    ]
    with pytest.raises(InvalidActivityTagError, match="Unknown"):
        await service._validate_tags([_entry(tag_id=99)])


@pytest.mark.asyncio
async def test_validate_tags_other_requires_label(service, activity_tag_repo):
    activity_tag_repo.list_predefined_ordered.return_value = [
        SimpleNamespace(id=9, name=ActivityTagRepository.OTHER_TAG_NAME),
    ]
    with pytest.raises(OtherTagRequiresLabelError):
        await service._validate_tags([_entry(tag_id=9, custom_label=None)])


@pytest.mark.asyncio
async def test_validate_tags_rejects_duplicate_tag_ids(service, activity_tag_repo):
    activity_tag_repo.list_predefined_ordered.return_value = [
        SimpleNamespace(id=1, name="Dev"),
    ]
    entry = TimesheetEntryRequest(
        project_id=1,
        hours=Decimal("4"),
        tags=[
            TimesheetEntryTagRequest(activity_tag_id=1),
            TimesheetEntryTagRequest(activity_tag_id=1),
        ],
    )
    with pytest.raises(InvalidActivityTagError, match="only once"):
        await service._validate_tags([entry])


@pytest.mark.asyncio
async def test_get_missed_reminder_shows_when_missing(
    service, resource_repo, timesheet_repo, allocation_repo
):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    allocation_repo.find_active_for_resource_in_week.return_value = [
        SimpleNamespace(id=1)
    ]
    timesheet_repo.find_by_resource_and_week.return_value = None

    result = await service.get_missed_reminder(SimpleNamespace(id=1))

    assert result.show_reminder is True
    assert result.week_start is not None
    assert "not been submitted" in result.message


@pytest.mark.asyncio
async def test_get_missed_reminder_hides_when_no_prior_week_allocation(
    service, resource_repo, timesheet_repo, allocation_repo
):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    allocation_repo.find_active_for_resource_in_week.return_value = []
    timesheet_repo.find_by_resource_and_week.return_value = None

    result = await service.get_missed_reminder(SimpleNamespace(id=1))

    assert result.show_reminder is False
    timesheet_repo.find_by_resource_and_week.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_missed_reminder_hides_when_submitted(
    service, resource_repo, timesheet_repo, allocation_repo
):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    allocation_repo.find_active_for_resource_in_week.return_value = [
        SimpleNamespace(id=1)
    ]
    timesheet_repo.find_by_resource_and_week.return_value = SimpleNamespace(
        status=TimesheetStatus.SUBMITTED
    )

    result = await service.get_missed_reminder(SimpleNamespace(id=1))

    assert result.show_reminder is False


@pytest.mark.asyncio
async def test_list_my_timesheets(service, resource_repo, timesheet_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    timesheet_repo.list_by_resource.return_value = [
        SimpleNamespace(
            id=1,
            week_start=date(2026, 7, 6),
            total_hours=Decimal("8"),
            status=TimesheetStatus.SUBMITTED,
        )
    ]

    result = await service.list_my_timesheets(SimpleNamespace(id=1))

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].status == TimesheetStatus.SUBMITTED


@pytest.mark.asyncio
async def test_list_team_timesheets_empty(service, resource_repo, allocation_repo):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=100)
    allocation_repo.find_on_manager_projects_in_week.return_value = []

    result = await service.list_team_timesheets(
        SimpleNamespace(id=1), date(2026, 7, 6)
    )

    assert result.week_start == date(2026, 7, 6)
    assert result.items == []


@pytest.mark.asyncio
async def test_list_team_timesheets_with_rows(
    service, resource_repo, allocation_repo, timesheet_repo
):
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=100)
    resource = SimpleNamespace(user=SimpleNamespace(full_name="Ada"))
    project = SimpleNamespace(id=5, name="Apollo")
    allocation = SimpleNamespace(
        resource_id=10,
        resource=resource,
        project=project,
    )
    allocation_repo.find_on_manager_projects_in_week.return_value = [allocation]
    timesheet = SimpleNamespace(
        id=3,
        resource_id=10,
        status=TimesheetStatus.SUBMITTED,
        entries=[SimpleNamespace(project_id=5, hours=Decimal("6"))],
    )
    timesheet_repo.find_by_resources_and_week.return_value = [timesheet]

    result = await service.list_team_timesheets(
        SimpleNamespace(id=1), date(2026, 7, 6)
    )

    assert len(result.items) == 1
    assert result.items[0].resource_name == "Ada"
    assert result.items[0].hours == Decimal("6")
    assert result.items[0].status == TimesheetStatus.SUBMITTED


@pytest.mark.asyncio
async def test_get_timesheet_detail_not_found(service, timesheet_repo):
    timesheet_repo.get_by_id_with_entries.return_value = None
    with pytest.raises(TimesheetNotFoundError):
        await service.get_timesheet_detail(99, SimpleNamespace(id=1))


@pytest.mark.asyncio
async def test_get_timesheet_detail_for_resource_owner(
    service, resource_repo, timesheet_repo
):
    from server.models.enums import UserRole

    user = SimpleNamespace(
        id=1, role=SimpleNamespace(name=UserRole.RESOURCE.value)
    )
    resource_repo.find_by_user_id.return_value = SimpleNamespace(id=10)
    entry = SimpleNamespace(
        project=SimpleNamespace(name="Apollo"),
        hours=Decimal("8"),
        tags=[
            SimpleNamespace(custom_label=None, activity_tag=SimpleNamespace(name="Dev")),
            SimpleNamespace(custom_label="Misc", activity_tag=SimpleNamespace(name="Other")),
        ],
    )
    timesheet = SimpleNamespace(
        id=3,
        resource_id=10,
        week_start=date(2026, 7, 6),
        status=TimesheetStatus.SUBMITTED,
        total_hours=Decimal("8"),
        entries=[entry],
    )
    timesheet_repo.get_by_id_with_entries.return_value = timesheet

    result = await service.get_timesheet_detail(3, user)

    assert result.id == 3
    assert result.entries[0].activity_tags == ["Dev", "Misc"]

    timesheet.resource_id = 99
    with pytest.raises(TimesheetNotFoundError):
        await service.get_timesheet_detail(3, user)


@pytest.mark.asyncio
async def test_mark_missed_timesheets_created_updated_skipped(
    service, allocation_repo, timesheet_repo
):
    week = date(2026, 6, 29)
    service._weeks_to_check = MagicMock(return_value=[week])
    allocation_repo.find_overlapping_week.return_value = [
        SimpleNamespace(resource_id=1),
        SimpleNamespace(resource_id=2),
        SimpleNamespace(resource_id=3),
    ]

    async def find_existing(resource_id, _week):
        if resource_id == 1:
            return None
        if resource_id == 2:
            return SimpleNamespace(
                status=TimesheetStatus.MISSED,
                total_hours=Decimal("1"),
                submitted_at="x",
            )
        return SimpleNamespace(status=TimesheetStatus.SUBMITTED)

    timesheet_repo.find_by_resource_and_week.side_effect = find_existing
    timesheet_repo.save.return_value = None

    result = await service.mark_missed_timesheets()

    assert result.created == 1
    assert result.updated == 1
    assert result.skipped == 1


@pytest.mark.asyncio
async def test_validate_tags_happy_path(service, activity_tag_repo):
    activity_tag_repo.list_predefined_ordered.return_value = [
        SimpleNamespace(id=1, name="Dev"),
        SimpleNamespace(id=9, name=ActivityTagRepository.OTHER_TAG_NAME),
    ]
    await service._validate_tags(
        [_entry(tag_id=1), _entry(project_id=2, tag_id=9, custom_label="Custom")]
    )
