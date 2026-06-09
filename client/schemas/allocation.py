from datetime import date

from pydantic import BaseModel


class AllocationSummaryResponse(BaseModel):
    id: int
    employee_name: str
    project_name: str
    utilisation_percent: int
    from_date: date
    to_date: date


class AllocationListResponse(BaseModel):
    items: list[AllocationSummaryResponse]
    total: int
    limit: int
    offset: int
