from datetime import date

from pydantic import BaseModel, Field


class CreateAllocationRequest(BaseModel):
    employee_id: int
    project_id: int
    utilisation_percent: int = Field(ge=1, le=100)
    from_date: date
    to_date: date
