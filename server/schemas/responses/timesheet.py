from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from server.schemas.response_values import TimesheetMessage


class TimesheetSummaryResponse(BaseModel):
    id: int
    week_start: date
    total_hours: Decimal
    status: str


class TimesheetListResponse(BaseModel):
    items: list[TimesheetSummaryResponse]


class TimesheetEntryDetailResponse(BaseModel):
    project_name: str
    hours: Decimal
    activity_tags: list[str]


class TimesheetDetailResponse(BaseModel):
    id: int
    week_start: date
    status: str
    total_hours: Decimal
    entries: list[TimesheetEntryDetailResponse]


class TimesheetSubmittedResponse(BaseModel):
    id: int
    message: TimesheetMessage
    week_start: date
    total_hours: Decimal
    status: str


class MissedReminderResponse(BaseModel):
    show_reminder: bool
    week_start: date | None = None
    message: str | None = None
