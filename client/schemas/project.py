from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ProjectSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    manager_name: str
    end_date: date
    status: str
    story_points_done: int
    story_points_total: int


class ProjectDetailResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    description: str | None
    start_date: date
    end_date: date
    status: str
    manager_id: int
    manager_name: str
    total_story_points: int


class ProjectListResponse(BaseModel):
    items: list[ProjectSummaryResponse]
    total: int
    limit: int
    offset: int


class ProjectCreatedResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    status: str
    message: str


class ProjectUpdatedResponse(BaseModel):
    id: int
    message: str


class ManagedProjectSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    status: str
    end_date: date
    health_status: str | None
    computed_at: datetime | None


class ManagedProjectListResponse(BaseModel):
    items: list[ManagedProjectSummaryResponse]


class ProjectRiskFlagResponse(BaseModel):
    flag_text: str
    is_positive: bool
    sort_order: int


class ManagerMilestoneResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    title: str
    due_date: date
    story_points: int
    status: str
    sort_order: int
    is_overdue: bool


class ManagerProjectAllocationResponse(BaseModel):
    resource_name: str
    utilisation_percent: int
    from_date: date
    to_date: date


class ManagerProjectDetailResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    end_date: date
    status: str
    health_status: str | None
    computed_at: datetime | None
    risk_flags: list[ProjectRiskFlagResponse]
    milestones: list[ManagerMilestoneResponse]
    allocations: list[ManagerProjectAllocationResponse]
