from pydantic import BaseModel


class ActivityTagResponse(BaseModel):
    id: int
    name: str
    display_order: int


class ActivityTagListResponse(BaseModel):
    items: list[ActivityTagResponse]
