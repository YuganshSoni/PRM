from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import UserRole
from server.routers.timesheet_router import TimesheetRouter
from server.schemas.response_values import TimesheetMessage
from server.schemas.responses.timesheet import (
    MissedReminderResponse,
    TeamTimesheetListResponse,
    TeamTimesheetRowResponse,
    TimesheetDetailResponse,
    TimesheetEntryDetailResponse,
    TimesheetSummaryResponse,
)
from server.schemas.responses.timesheet_compliance import TeamComplianceRowResponse


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(TimesheetRouter().router)
    return application


def _user(role: UserRole):
    user = MagicMock()
    user.id = 1
    user.force_password_change = False
    user.role = SimpleNamespace(name=role.value)
    return user


def _bind(app: FastAPI, user, *, timesheet_service=None, compliance_service=None):
    async def override_user():
        return user

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    if timesheet_service is not None:

        async def override_ts():
            return timesheet_service

        app.dependency_overrides[dependency_provider.get_timesheet_service] = override_ts
    if compliance_service is not None:

        async def override_cs():
            return compliance_service

        app.dependency_overrides[
            dependency_provider.get_timesheet_compliance_service
        ] = override_cs


def test_submit_timesheet(app: FastAPI):
    service = AsyncMock()
    timesheet = SimpleNamespace(
        id=4,
        week_start=date(2026, 7, 13),
        total_hours=Decimal("8.0"),
        status="SUBMITTED",
    )
    service.submit_timesheet.return_value = timesheet
    resource = _user(UserRole.RESOURCE)
    _bind(app, resource, timesheet_service=service)
    client = TestClient(app)

    response = client.post(
        "/timesheets",
        json={
            "week_start": "2026-07-13",
            "entries": [
                {
                    "project_id": 3,
                    "hours": "8.0",
                    "tags": [{"activity_tag_id": 1}],
                }
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == TimesheetMessage.TIMESHEET_SUBMITTED
    assert body["id"] == 4
    service.submit_timesheet.assert_awaited_once()


def test_list_my_timesheets(app: FastAPI):
    service = AsyncMock()
    service.list_my_timesheets.return_value = [
        TimesheetSummaryResponse(
            id=4,
            week_start=date(2026, 7, 13),
            total_hours=Decimal("8.0"),
            status="SUBMITTED",
        )
    ]
    resource = _user(UserRole.RESOURCE)
    _bind(app, resource, timesheet_service=service)
    client = TestClient(app)

    response = client.get("/timesheets/mine")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == 4


def test_get_missed_reminder(app: FastAPI):
    service = AsyncMock()
    service.get_missed_reminder.return_value = MissedReminderResponse(
        show_reminder=True,
        week_start=date(2026, 7, 6),
        message="Submit last week",
    )
    resource = _user(UserRole.RESOURCE)
    _bind(app, resource, timesheet_service=service)
    client = TestClient(app)

    response = client.get("/timesheets/mine/missed-reminder")

    assert response.status_code == 200
    assert response.json()["show_reminder"] is True


def test_list_team_timesheets(app: FastAPI):
    service = AsyncMock()
    service.list_team_timesheets.return_value = TeamTimesheetListResponse(
        week_start=date(2026, 7, 13),
        items=[
            TeamTimesheetRowResponse(
                resource_id=2,
                resource_name="Ada",
                project_id=3,
                project_name="Apollo",
                hours=Decimal("8.0"),
                status="SUBMITTED",
                timesheet_id=4,
            )
        ],
    )
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, timesheet_service=service)
    client = TestClient(app)

    response = client.get("/timesheets/team?week_start=2026-07-13")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["resource_name"] == "Ada"
    service.list_team_timesheets.assert_awaited_once_with(
        manager, date(2026, 7, 13)
    )


def test_compliance_team_and_restore(app: FastAPI):
    compliance = AsyncMock()
    compliance.list_team_compliance_rows.return_value = [
        TeamComplianceRowResponse(
            resource_id=2,
            resource_name="Ada",
            week_start=date(2026, 7, 6),
            status="FROZEN",
            frozen_at=date(2026, 7, 10),
        )
    ]
    record = SimpleNamespace(
        resource_id=2, week_start=date(2026, 7, 6), status="RESTORED"
    )
    compliance.restore_access.return_value = record
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, compliance_service=compliance)
    client = TestClient(app)

    listed = client.get("/timesheets/compliance/team")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["status"] == "FROZEN"

    restored = client.post(
        "/timesheets/compliance/2/restore?week_start=2026-07-06"
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "RESTORED"
    compliance.restore_access.assert_awaited_once_with(
        manager, 2, date(2026, 7, 6)
    )


def test_get_timesheet_detail(app: FastAPI):
    service = AsyncMock()
    service.get_timesheet_detail.return_value = TimesheetDetailResponse(
        id=4,
        week_start=date(2026, 7, 13),
        status="SUBMITTED",
        total_hours=Decimal("8.0"),
        entries=[
            TimesheetEntryDetailResponse(
                project_name="Apollo",
                hours=Decimal("8.0"),
                activity_tags=["Development"],
            )
        ],
    )
    manager = _user(UserRole.MANAGER)
    _bind(app, manager, timesheet_service=service)
    client = TestClient(app)

    response = client.get("/timesheets/4")

    assert response.status_code == 200
    body = response.json()
    assert body["entries"][0]["project_name"] == "Apollo"
    service.get_timesheet_detail.assert_awaited_once_with(4, manager)
