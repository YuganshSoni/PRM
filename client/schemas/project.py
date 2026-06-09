from datetime import date

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
