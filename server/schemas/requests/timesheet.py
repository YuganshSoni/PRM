from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class TimesheetEntryTagRequest(BaseModel):
    activity_tag_id: int
    custom_label: str | None = None


class TimesheetEntryRequest(BaseModel):
    project_id: int
    hours: Decimal = Field(ge=0)
    tags: list[TimesheetEntryTagRequest] = Field(min_length=1)


class SubmitTimesheetRequest(BaseModel):
    week_start: date
    entries: list[TimesheetEntryRequest] = Field(min_length=1)
