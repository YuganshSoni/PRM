from datetime import date

from pydantic import BaseModel, Field

from server.models.enums import ProjectStatus


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    start_date: date
    end_date: date
    status: ProjectStatus
    manager_id: int = Field(ge=1)
    total_story_points: int = Field(ge=0)


class UpdateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    start_date: date
    end_date: date
    status: ProjectStatus
    manager_id: int = Field(ge=1)
    total_story_points: int = Field(ge=0)
