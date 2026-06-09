from datetime import date

from pydantic import BaseModel, ConfigDict

from server.models.enums import ProjectStatus
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


class ManagedProjectListResponse(BaseModel):
    items: list[ManagedProjectSummaryResponse]
