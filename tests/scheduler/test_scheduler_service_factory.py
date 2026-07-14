from unittest.mock import MagicMock, patch

import pytest

from server.scheduler.scheduler_service import SchedulerService
from server.scheduler.scheduler_service_factory import SchedulerServiceFactory


@pytest.mark.asyncio
async def test_scheduler_service_factory_create_wires_dependencies():
    session = MagicMock()
    session_factory = MagicMock(return_value=session)
    factory = SchedulerServiceFactory(session_factory)

    bundle = MagicMock()
    bundle.allocation_notification_service = MagicMock()
    bundle.compliance_service = MagicMock()
    bundle.at_risk_notification_service = MagicMock()

    with (
        patch(
            "server.scheduler.scheduler_service_factory.build_notification_bundle",
            return_value=bundle,
        ) as build_bundle,
        patch(
            "server.scheduler.scheduler_service_factory.AllocationRepository"
        ) as allocation_cls,
        patch(
            "server.scheduler.scheduler_service_factory.ResourceRepository"
        ) as resource_cls,
        patch(
            "server.scheduler.scheduler_service_factory.ResourceStatusRepository"
        ) as status_cls,
        patch(
            "server.scheduler.scheduler_service_factory.ProjectRepository"
        ) as project_cls,
        patch(
            "server.scheduler.scheduler_service_factory.SystemConfigRepository"
        ) as config_cls,
        patch(
            "server.scheduler.scheduler_service_factory.TimesheetRepository"
        ) as timesheet_cls,
        patch(
            "server.scheduler.scheduler_service_factory.TimesheetEntryRepository"
        ),
        patch(
            "server.scheduler.scheduler_service_factory.TimesheetEntryTagRepository"
        ),
        patch(
            "server.scheduler.scheduler_service_factory.ActivityTagRepository"
        ),
        patch(
            "server.scheduler.scheduler_service_factory.MilestoneRepository"
        ),
        patch(
            "server.scheduler.scheduler_service_factory.ProjectHealthRepository"
        ),
        patch(
            "server.scheduler.scheduler_service_factory.ProjectRiskFlagRepository"
        ),
        patch(
            "server.scheduler.scheduler_service_factory.AllocationService"
        ) as allocation_service_cls,
        patch(
            "server.scheduler.scheduler_service_factory.TimesheetService"
        ) as timesheet_service_cls,
        patch(
            "server.scheduler.scheduler_service_factory.ProjectHealthService"
        ) as health_service_cls,
        patch(
            "server.scheduler.scheduler_service_factory.SchedulerService"
        ) as scheduler_cls,
    ):
        for cls in (
            allocation_cls,
            resource_cls,
            status_cls,
            project_cls,
            config_cls,
            timesheet_cls,
        ):
            cls.return_value = MagicMock()
        allocation_service_cls.return_value = MagicMock()
        timesheet_service_cls.return_value = MagicMock()
        health_service_cls.return_value = MagicMock()
        expected = MagicMock(spec=SchedulerService)
        scheduler_cls.return_value = expected

        result = await factory.create()

    assert result is expected
    build_bundle.assert_called_once_with(session)
    session_factory.assert_called_once_with()
    scheduler_cls.assert_called_once()
