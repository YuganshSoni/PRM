from datetime import date

from pydantic import BaseModel


class TeamComplianceRowResponse(BaseModel):
    resource_id: int
    resource_name: str
    week_start: date
    status: str
    frozen_at: date | None = None


class TeamComplianceListResponse(BaseModel):
    items: list[TeamComplianceRowResponse]


class ComplianceRestoreResponse(BaseModel):
    resource_id: int
    week_start: date
    status: str
    message: str
