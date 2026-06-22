from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AllocationSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    employee_name: str = Field(validation_alias="resource_name")
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
    model_config = ConfigDict(populate_by_name=True)

    id: int
    message: str
    employee_name: str = Field(validation_alias="resource_name")
    project_name: str
    utilisation_percent: int
    from_date: date
    to_date: date


class AllocationEndedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    employee_name: str = Field(validation_alias="resource_name")
    project_name: str
    end_date: date


class ProjectAllocationSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    employee_id: int = Field(validation_alias="resource_id")
    employee_name: str = Field(validation_alias="resource_name")
    utilisation_percent: int
    from_date: date
    to_date: date


class ProjectAllocationListResponse(BaseModel):
    project_name: str
    items: list[ProjectAllocationSummaryResponse]


class MyAllocationSummaryResponse(BaseModel):
    project_name: str
    utilisation_percent: int
    from_date: date
    to_date: date
    status: str


class MyAllocationListResponse(BaseModel):
    items: list[MyAllocationSummaryResponse]
    total_utilisation_percent: int


class WeekProjectAllocationResponse(BaseModel):
    project_id: int
    project_name: str
    utilisation_percent: int
    max_hours: float


class WeekAllocationContextResponse(BaseModel):
    week_start: date
    max_weekly_hours: int
    projects: list[WeekProjectAllocationResponse]


class BulkAllocationItemRequest(BaseModel):
    resource_id: int
    role_key: str | None = None


class BulkCreateAllocationRequest(BaseModel):
    project_id: int
    utilisation_percent: int
    from_date: date
    to_date: date
    items: list[BulkAllocationItemRequest]


class BulkAllocationCreatedItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    employee_id: int = Field(validation_alias="resource_id")
    employee_name: str = Field(validation_alias="resource_name")
    role_key: str | None = None
    utilisation_percent: int
    from_date: date
    to_date: date


class BulkAllocationCreatedResponse(BaseModel):
    project_id: int
    project_name: str
    message: str
    items: list[BulkAllocationCreatedItemResponse]
