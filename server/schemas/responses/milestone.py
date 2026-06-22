from datetime import date

from pydantic import BaseModel, ConfigDict

from server.models.enums import MilestoneStatus
from server.schemas.response_values import MilestoneMessage


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
    status: MilestoneStatus
    sort_order: int


class MilestoneListResponse(BaseModel):
    items: list[MilestoneResponse]
    story_point_summary: StoryPointSummary


class MilestoneUpdatedResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    status: MilestoneStatus
    message: MilestoneMessage
