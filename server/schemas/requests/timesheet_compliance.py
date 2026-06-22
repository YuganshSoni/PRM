from datetime import date

from pydantic import BaseModel


class RestoreTimesheetComplianceRequest(BaseModel):
    week_start: date
