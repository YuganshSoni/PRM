from datetime import date

from pydantic import BaseModel, ConfigDict


class StoryPointSummary(BaseModel):
    total: int
    completed: int
    remaining: int


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    title: str
    due_date: date
    story_points: int
    status: str
    sort_order: int


class MilestoneListResponse(BaseModel):
    items: list[MilestoneResponse]
    story_point_summary: StoryPointSummary


class MilestoneUpdatedResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    status: str
    message: str
