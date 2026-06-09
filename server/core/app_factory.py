from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.core.database import get_database_manager
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.routers.auth_router import AuthRouter
from server.routers.employee_router import EmployeeRouter
from server.routers.health_router import HealthRouter
from server.routers.milestone_router import MilestoneRouter
from server.routers.project_router import ProjectRouter
from server.routers.skill_router import SkillRouter
from server.routers.user_router import UserRouter


class ApplicationFactory:
    def create(self) -> FastAPI:
        app = FastAPI(lifespan=self.lifespan, debug=False)
        ExceptionHandlerRegistrar().register(app)
        app.include_router(HealthRouter().router)
        app.include_router(AuthRouter().router)
        app.include_router(UserRouter().router)
        app.include_router(EmployeeRouter().router)
        app.include_router(SkillRouter().router)
        app.include_router(ProjectRouter().router)
        app.include_router(MilestoneRouter().router)
        return app

    @asynccontextmanager
    async def lifespan(self, _app: FastAPI) -> AsyncIterator[None]:
        yield
        await get_database_manager().dispose()
