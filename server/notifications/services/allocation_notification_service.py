from server.models.allocation import Allocation
from server.models.enums import NotificationType
from server.notifications.dto.notification_dto import (
    AllocationConfirmationContext,
    NotificationIntent,
)
from server.notifications.services.notification_service import NotificationService
from server.notifications.templates.email_templates import EmailTemplateRenderer
from server.services.resource_mapper import ResourceMapper


class AllocationNotificationService:
    def __init__(self, notification_service: NotificationService) -> None:
        self._notification_service = notification_service

    async def send_allocation_confirmation(self, allocation: Allocation) -> None:
        resource = allocation.resource
        project = allocation.project
        if resource is None or project is None or resource.user is None:
            return

        subject, body = EmailTemplateRenderer.allocation_confirmation(
            AllocationConfirmationContext(
                resource_name=ResourceMapper.full_name(resource),
                project_name=project.name,
                from_date=allocation.from_date,
                to_date=allocation.to_date,
                utilisation_percent=allocation.utilisation_percent,
            )
        )
        await self._notification_service.send(
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
