import logging

from server.models.allocation import Allocation
from server.models.enums import NotificationType
from server.notifications.dto.notification_dto import (
    AllocationConfirmationContext,
    NotificationIntent,
)
from server.notifications.services.notification_service import NotificationService
from server.notifications.templates.email_templates import EmailTemplateRenderer
from server.services.resource_mapper import ResourceMapper

logger = logging.getLogger(__name__)


class AllocationNotificationService:
    def __init__(self, notification_service: NotificationService) -> None:
        self._notification_service = notification_service

    async def send_allocation_confirmation(self, allocation: Allocation) -> None:
        resource = allocation.resource
        project = allocation.project
        if resource is None or project is None or resource.user is None:
            logger.warning(
                "Allocation confirmation skipped: allocation_id=%s "
                "(resource=%s project=%s user=%s)",
                allocation.id,
                resource is not None,
                project is not None,
                resource is not None and resource.user is not None,
            )
            return

        logger.info(
            "Allocation confirmation triggered: allocation_id=%s resource_id=%s "
            "project=%r to=%s",
            allocation.id,
            resource.id,
            project.name,
            resource.user.email,
        )
        subject, body = EmailTemplateRenderer.allocation_confirmation(
            AllocationConfirmationContext(
                resource_name=ResourceMapper.full_name(resource),
                project_name=project.name,
                from_date=allocation.from_date,
                to_date=allocation.to_date,
                utilisation_percent=allocation.utilisation_percent,
            )
        )
        sent = await self._notification_service.send(
            NotificationIntent(
                notification_type=NotificationType.ALLOCATION_CONFIRMATION,
                dedupe_key=f"allocation:{allocation.id}:confirmation",
                to_email=resource.user.email,
                subject=subject,
                body=body,
                entity_type="allocation",
                entity_id=allocation.id,
            )
        )
        if not sent:
            logger.warning(
                "Allocation confirmation not delivered: allocation_id=%s to=%s",
                allocation.id,
                resource.user.email,
            )
