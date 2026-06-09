from datetime import date

from pydantic import BaseModel

from server.schemas.response_values import AllocationMessage


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


class AllocationCreatedResponse(BaseModel):
    id: int
    message: AllocationMessage
    employee_name: str
    project_name: str
    utilisation_percent: int
    from_date: date
    to_date: date


class AllocationEndedResponse(BaseModel):
    message: AllocationMessage
    employee_name: str
    project_name: str
    end_date: date


class ProjectAllocationSummaryResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    utilisation_percent: int
    from_date: date
    to_date: date


class ProjectAllocationListResponse(BaseModel):
    project_name: str
    items: list[ProjectAllocationSummaryResponse]
