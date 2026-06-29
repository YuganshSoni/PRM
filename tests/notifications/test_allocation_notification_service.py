from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.models.enums import NotificationType
from server.notifications.services.allocation_notification_service import (
    AllocationNotificationService,
)


def _allocation(
    *,
    with_resource: bool = True,
    with_project: bool = True,
    with_user: bool = True,
):
    allocation = MagicMock()
    allocation.id = 42
    allocation.from_date = date(2026, 1, 1)
    allocation.to_date = date(2026, 6, 30)
    allocation.utilisation_percent = 80

    if not with_resource:
        allocation.resource = None
    else:
        resource = MagicMock()
        resource.id = 7
        resource.user = None
        if with_user:
            user = MagicMock()
            user.email = "ada@example.com"
            user.full_name = "Ada Lovelace"
            resource.user = user
        allocation.resource = resource

    if not with_project:
        allocation.project = None
    else:
        project = MagicMock()
        project.name = "Engine"
        allocation.project = project

    return allocation


@pytest.mark.asyncio
async def test_skips_when_resource_missing():
    notification_service = AsyncMock()
    service = AllocationNotificationService(notification_service)

    await service.send_allocation_confirmation(_allocation(with_resource=False))

    notification_service.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_skips_when_project_missing():
    notification_service = AsyncMock()
    service = AllocationNotificationService(notification_service)

    await service.send_allocation_confirmation(_allocation(with_project=False))

    notification_service.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_skips_when_user_missing():
    notification_service = AsyncMock()
    service = AllocationNotificationService(notification_service)

    await service.send_allocation_confirmation(_allocation(with_user=False))

    notification_service.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_sends_allocation_confirmation_intent():
    notification_service = AsyncMock()
    notification_service.send.return_value = True
    service = AllocationNotificationService(notification_service)

    await service.send_allocation_confirmation(_allocation())

    notification_service.send.assert_awaited_once()
    intent = notification_service.send.await_args.args[0]
    assert intent.notification_type == NotificationType.ALLOCATION_CONFIRMATION
    assert intent.dedupe_key == "allocation:42:confirmation"
    assert intent.to_email == "ada@example.com"
    assert intent.subject == "Project Allocation: Engine"
    assert "Ada Lovelace" in intent.body
    assert "Engine" in intent.body
    assert "80% utilization" in intent.body
    assert intent.entity_type == "allocation"
    assert intent.entity_id == 42


@pytest.mark.asyncio
async def test_logs_when_delivery_fails():
    notification_service = AsyncMock()
    notification_service.send.return_value = False
    service = AllocationNotificationService(notification_service)

    await service.send_allocation_confirmation(_allocation())

    notification_service.send.assert_awaited_once()
