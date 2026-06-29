from unittest.mock import MagicMock, patch

from server.notifications.notification_wiring import (
    NotificationBundle,
    build_notification_bundle,
)
from server.notifications.services.allocation_notification_service import (
    AllocationNotificationService,
)
from server.notifications.services.at_risk_notification_service import (
    AtRiskNotificationService,
)
from server.notifications.services.notification_service import NotificationService
from server.services.timesheet_compliance_service import TimesheetComplianceService


def test_build_notification_bundle_wires_services():
    session = MagicMock()

    with (
        patch(
            "server.notifications.notification_wiring.SystemConfigRepository"
        ) as config_cls,
        patch(
            "server.notifications.notification_wiring.NotificationLogRepository"
        ) as log_cls,
        patch(
            "server.notifications.notification_wiring.ResourceRepository"
        ) as resource_cls,
        patch(
            "server.notifications.notification_wiring.TimesheetRepository"
        ) as timesheet_cls,
        patch(
            "server.notifications.notification_wiring.AllocationRepository"
        ) as allocation_cls,
        patch(
            "server.notifications.notification_wiring.ProjectRepository"
        ) as project_cls,
        patch(
            "server.notifications.notification_wiring.MilestoneRepository"
        ) as milestone_cls,
        patch(
            "server.notifications.notification_wiring.TimesheetComplianceRepository"
        ) as compliance_repo_cls,
        patch(
            "server.notifications.notification_wiring.ProjectHealthRepository"
        ) as health_repo_cls,
        patch(
            "server.notifications.notification_wiring.ProjectRiskFlagRepository"
        ) as risk_repo_cls,
    ):
        for cls in (
            config_cls,
            log_cls,
            resource_cls,
            timesheet_cls,
            allocation_cls,
            project_cls,
            milestone_cls,
            compliance_repo_cls,
            health_repo_cls,
            risk_repo_cls,
        ):
            cls.return_value = MagicMock()

        bundle = build_notification_bundle(session)

    assert isinstance(bundle, NotificationBundle)
    assert isinstance(bundle.notification_service, NotificationService)
    assert isinstance(
        bundle.allocation_notification_service, AllocationNotificationService
    )
    assert isinstance(bundle.compliance_service, TimesheetComplianceService)
    assert isinstance(
        bundle.at_risk_notification_service, AtRiskNotificationService
    )
    config_cls.assert_called_once_with(session)
    log_cls.assert_called_once_with(session)
