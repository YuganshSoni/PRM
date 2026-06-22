from datetime import date

from pydantic import BaseModel, Field, model_validator


class CreateAllocationRequest(BaseModel):
    resource_id: int
    project_id: int
    utilisation_percent: int = Field(ge=1, le=100)
    from_date: date
    to_date: date


class BulkAllocationItemRequest(BaseModel):
    resource_id: int
    role_key: str | None = None


class BulkCreateAllocationRequest(BaseModel):
    project_id: int
    utilisation_percent: int = Field(ge=1, le=100)
    from_date: date
    to_date: date
    items: list[BulkAllocationItemRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_resources(self) -> "BulkCreateAllocationRequest":
        resource_ids = [item.resource_id for item in self.items]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("Duplicate resource_id values are not allowed in bulk items")
        return self
