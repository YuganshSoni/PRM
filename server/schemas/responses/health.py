from pydantic import BaseModel, ConfigDict

from server.schemas.response_values import ApiStatus, DatabaseConnectionStatus


class HealthStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: ApiStatus


class HealthDatabaseResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: ApiStatus
    database: DatabaseConnectionStatus
