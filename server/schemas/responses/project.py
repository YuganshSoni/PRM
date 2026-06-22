from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from server.models.enums import HealthStatus, MilestoneStatus, ProjectStatus
from server.schemas.response_values import ProjectMessage


class ProjectSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    manager_name: str
    end_date: date
    status: ProjectStatus
    story_points_done: int
    story_points_total: int


class ProjectDetailResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    description: str | None
    start_date: date
    end_date: date
    status: ProjectStatus
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
    status: ProjectStatus
    message: ProjectMessage


class ProjectUpdatedResponse(BaseModel):
    id: int
    message: ProjectMessage


class ManagedProjectSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    status: ProjectStatus
    end_date: date
    health_status: HealthStatus | None
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
    status: MilestoneStatus
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
    status: ProjectStatus
    health_status: HealthStatus | None
    computed_at: datetime | None
    risk_flags: list[ProjectRiskFlagResponse]
    milestones: list[ManagerMilestoneResponse]
    allocations: list[ManagerProjectAllocationResponse]
