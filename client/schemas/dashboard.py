from datetime import date

from pydantic import BaseModel


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
    bench_employees: list[BenchEmployeeSummary]
    active_employees: list[ActiveEmployeeSummary]
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
