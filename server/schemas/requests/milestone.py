from datetime import date

from pydantic import BaseModel, Field

from server.models.enums import MilestoneStatus


class AddMilestoneRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date
    story_points: int = Field(gt=0)


class UpdateMilestoneStatusRequest(BaseModel):
    status: MilestoneStatus
