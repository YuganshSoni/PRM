from server.models.enums import NotificationDeliveryStatus
from server.models.notification_log import NotificationLog
from server.models.system_config import SystemConfig
from server.notifications.dto.notification_dto import EmailMessage, NotificationIntent
from server.notifications.gateways.email_gateway import EmailGatewayFactory
from server.repositories.notification_log_repository import NotificationLogRepository
from server.repositories.system_config_repository import SystemConfigRepository


class NotificationService:
    def __init__(
        self,
        config_repository: SystemConfigRepository,
        log_repository: NotificationLogRepository,
    ) -> None:
        self._config_repository = config_repository
        self._log_repository = log_repository

    async def send(self, intent: NotificationIntent) -> bool:
        if not intent.to_email.strip():
            return False

        if await self._log_repository.exists(
            intent.notification_type, intent.dedupe_key, intent.to_email
        ):
            await self._log_repository.save(
                NotificationLog(
                    notification_type=intent.notification_type,
                    dedupe_key=intent.dedupe_key,
                    recipient_email=intent.to_email,
                    subject=intent.subject,
                    entity_type=intent.entity_type,
                    entity_id=intent.entity_id,
                    status=NotificationDeliveryStatus.SKIPPED_DUPLICATE,
                )
            )
            return False

        config = await self._config_repository.get()
        if config is None:
            return False

        gateway = EmailGatewayFactory.create(config)
        result = await gateway.send(
            EmailMessage(
                to_email=intent.to_email,
                subject=intent.subject,
                body=intent.body,
            )
        )

        status = (
            NotificationDeliveryStatus.SENT
            if result.success
            else NotificationDeliveryStatus.FAILED
        )
        await self._log_repository.save(
            NotificationLog(
                notification_type=intent.notification_type,
                dedupe_key=intent.dedupe_key,
                recipient_email=intent.to_email,
                subject=intent.subject,
                entity_type=intent.entity_type,
                entity_id=intent.entity_id,
                status=status,
                error_message=result.error_message,
            )
        )
        return result.success

    async def get_config(self) -> SystemConfig | None:
        return await self._config_repository.get()
