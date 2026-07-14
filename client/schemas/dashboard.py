from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BenchEmployeeSummary(BaseModel):
    id: int
    full_name: str
    department: str
    skills: list[str]


class ActiveEmployeeSummary(BaseModel):
    id: int
    full_name: str
    utilisation_percent: int
    availability_label: str


class DashboardStatsResponse(BaseModel):
    bench_count: int
    partial_count: int


class ResourceDashboardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    bench_employees: list[BenchEmployeeSummary] = Field(
        validation_alias="bench_resources"
    )
    active_employees: list[ActiveEmployeeSummary] = Field(
        validation_alias="active_resources"
    )
    stats: DashboardStatsResponse
    month_label: str


class DashboardAllocationSummary(BaseModel):
    project_name: str
    utilisation_percent: int
    from_date: date
    to_date: date


class DashboardEmployeeDetailResponse(BaseModel):
    id: int
    full_name: str
    department: str
    status: str
    utilisation_percent: int
    skills: list[str]
    active_allocations: list[DashboardAllocationSummary]
    recent_activity_tags: list[str]
