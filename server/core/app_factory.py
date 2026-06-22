from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.core.config import get_settings
from server.core.database import get_database_manager
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.core.exceptions import SystemConfigNotFoundError
from server.core.logging_config import LoggingConfigurator
from server.core.middleware import (
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from server.repositories.system_config_repository import SystemConfigRepository
from server.routers.ai_router import AIRouter
from server.routers.activity_tag_router import ActivityTagRouter
from server.routers.allocation_router import AllocationRouter
from server.routers.auth_router import AuthRouter
from server.routers.config_router import ConfigRouter
from server.routers.dashboard_router import DashboardRouter
from server.routers.resource_router import EmployeeRouter
from server.routers.health_router import HealthRouter
from server.routers.milestone_router import MilestoneRouter
from server.routers.project_router import ProjectRouter
from server.routers.skill_router import SkillRouter
from server.routers.timesheet_router import TimesheetRouter
from server.routers.user_router import UserRouter
from server.scheduler.registry import set_scheduler_manager
from server.scheduler.scheduler_manager import SchedulerManager
from server.scheduler.scheduler_service_factory import SchedulerServiceFactory


class ApplicationFactory:
    def create(self) -> FastAPI:
        settings = get_settings()
        LoggingConfigurator().configure(settings)
        app = FastAPI(lifespan=self.lifespan, debug=False)
        ExceptionHandlerRegistrar().register(app)
        self._register_middleware(app, settings)
        app.include_router(HealthRouter().router)
        app.include_router(AuthRouter().router)
        app.include_router(UserRouter().router)
        app.include_router(EmployeeRouter().router)
        app.include_router(SkillRouter().router)
        app.include_router(ProjectRouter().router)
        app.include_router(MilestoneRouter().router)
        app.include_router(ConfigRouter().router)
        app.include_router(AllocationRouter().router)
        app.include_router(AIRouter().router)
        app.include_router(DashboardRouter().router)
        app.include_router(TimesheetRouter().router)
        app.include_router(ActivityTagRouter().router)
        return app

    def _register_middleware(self, app: FastAPI, settings) -> None:
        if settings.cors_origin_list:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=settings.cors_origin_list,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        app.add_middleware(RateLimitMiddleware, settings=settings)
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestIdMiddleware)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        settings = get_settings()
        db_manager = get_database_manager()
        scheduler_manager: SchedulerManager | None = None

        if settings.scheduler_enabled:
            factory = SchedulerServiceFactory(db_manager.session_factory)
            scheduler_manager = SchedulerManager(
                factory.create,
                compliance_factory=factory.create,
            )
            interval_hours = await self._load_scheduler_interval(db_manager)
            await scheduler_manager.start(interval_hours)
            set_scheduler_manager(scheduler_manager)
            app.state.scheduler_manager = scheduler_manager

        yield

        if scheduler_manager is not None:
            await scheduler_manager.shutdown()
            set_scheduler_manager(None)

        await db_manager.dispose()

    async def _load_scheduler_interval(self, db_manager) -> int:
        async with db_manager.session_factory() as session:
            config = await SystemConfigRepository(session).get()
            if config is None:
                raise SystemConfigNotFoundError("System configuration not found")
            return config.scheduler_interval_hours
