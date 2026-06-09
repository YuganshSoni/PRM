from datetime import date

from pydantic import BaseModel, ConfigDict

from server.models.enums import EmployeeStatus


class ActiveAllocationPreview(BaseModel):
    project_name: str
    utilisation_percent: int
    to_date: date


class EmployeeSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    full_name: str
    department: str
    status: EmployeeStatus
    is_active: bool


class EmployeeDetailResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    user_id: int
    full_name: str
    email: str
    department: str
    designation: str
    status: EmployeeStatus
    is_active: bool
    manager_id: int | None
    active_allocations: list[ActiveAllocationPreview]


class EmployeeListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    items: list[EmployeeSummaryResponse]
    total: int
    bench_count: int
    allocated_count: int
    limit: int
    offset: int


class EmployeeUpsertResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    user_id: int
    status: EmployeeStatus
    message: str
    created: bool


class AssignManagerResponse(BaseModel):
    employee_id: int
    manager_id: int
    message: str


class EmployeeActionResponse(BaseModel):
    employee_id: int
    message: str
