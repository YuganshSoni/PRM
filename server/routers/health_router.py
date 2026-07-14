from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.core.exceptions import DatabaseUnavailableError
from server.schemas.response_values import ApiStatus, DatabaseConnectionStatus
from server.schemas.responses.health import HealthDatabaseResponse, HealthStatusResponse


class HealthRouter:
    def __init__(self) -> None:
        self.router = APIRouter(tags=["health"])
        self.router.add_api_route(
            "/health",
            self.health,
            methods=["GET"],
            response_model=HealthStatusResponse,
        )
        self.router.add_api_route(
            "/health/db",
            self.health_db,
            methods=["GET"],
            response_model=HealthDatabaseResponse,
        )

    async def health(self) -> HealthStatusResponse:
        return HealthStatusResponse(status=ApiStatus.OK)

    async def health_db(self, db: AsyncSession = Depends(get_db)) -> HealthDatabaseResponse:
        try:
            await db.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise DatabaseUnavailableError("Database unavailable") from exc
        return HealthDatabaseResponse(
            status=ApiStatus.OK,
            database=DatabaseConnectionStatus.CONNECTED,
        )
