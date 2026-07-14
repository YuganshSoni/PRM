from unittest.mock import AsyncMock, MagicMock, patch

from starlette.testclient import TestClient

from server.core.app_factory import ApplicationFactory


class _SessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return None


def test_create_app_registers_routes_with_patched_bootstrap():
    settings = MagicMock()
    settings.cors_origin_list = ["http://localhost:3000"]
    settings.scheduler_enabled = False
    settings.log_format = "text"
    settings.rate_limit_enabled = False
    settings.rate_limit_requests = 100
    settings.rate_limit_window_seconds = 60

    session = AsyncMock()
    session.commit = AsyncMock()

    db_manager = MagicMock()
    db_manager.session_factory = MagicMock(return_value=_SessionCM(session))
    db_manager.dispose = AsyncMock()

    with (
        patch("server.core.app_factory.get_settings", return_value=settings),
        patch("server.core.app_factory.LoggingConfigurator") as logging_cls,
        patch(
            "server.core.app_factory.get_database_manager", return_value=db_manager
        ),
        patch("server.core.app_factory.SmtpConfigBootstrap") as smtp_boot,
        patch("server.core.app_factory.LlmConfigBootstrap") as llm_boot,
        patch("server.core.app_factory.SchedulerServiceFactory") as sched_factory,
        patch("server.core.app_factory.SchedulerManager") as sched_manager,
        patch("server.core.app_factory.set_scheduler_manager") as set_sched,
        patch("server.seed.seed_runner.SeedRunner", create=True),
    ):
        smtp_boot.apply_from_env = AsyncMock()
        llm_boot.apply_from_env = AsyncMock()
        logging_cls.return_value.configure = MagicMock()

        app = ApplicationFactory().create()
        paths = set(app.openapi()["paths"])

        assert "/health" in paths
        assert "/auth/login" in paths
        assert "/users" in paths
        assert "/resources" in paths
        assert "/projects" in paths
        assert "/allocations" in paths
        assert "/dashboard/resources" in paths
        assert "/timesheets" in paths
        assert "/activity-tags" in paths
        assert "/config" in paths

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

        smtp_boot.apply_from_env.assert_awaited()
        llm_boot.apply_from_env.assert_awaited()
        sched_factory.assert_not_called()
        sched_manager.assert_not_called()
        set_sched.assert_not_called()
        db_manager.dispose.assert_awaited()
        logging_cls.return_value.configure.assert_called_once_with(settings)
