from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from starlette.testclient import TestClient

from server.core.database import get_db
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.routers.health_router import HealthRouter
from server.schemas.response_values import ApiStatus, DatabaseConnectionStatus


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(HealthRouter().router)
    return application


def test_health_ok(app: FastAPI):
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == ApiStatus.OK


def test_health_db_connected(app: FastAPI):
    session = AsyncMock()
    session.execute = AsyncMock(return_value=None)

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.get("/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ApiStatus.OK
    assert body["database"] == DatabaseConnectionStatus.CONNECTED


def test_health_db_unavailable(app: FastAPI):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=SQLAlchemyError("down"))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.get("/health/db")

    assert response.status_code == 503
