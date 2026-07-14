import logging

from server.models.enums import NotificationDeliveryStatus
from server.models.notification_log import NotificationLog
from server.models.system_config import SystemConfig
from server.notifications.dto.notification_dto import EmailMessage, NotificationIntent
from server.notifications.gateways.email_gateway import (
    EmailGatewayFactory,
    LoggingEmailGateway,
    SmtpEmailGateway,
)
from server.repositories.notification_log_repository import NotificationLogRepository
from server.repositories.system_config_repository import SystemConfigRepository

logger = logging.getLogger(__name__)


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
            logger.warning(
                "Notification skipped: empty recipient (type=%s dedupe_key=%s)",
                intent.notification_type,
                intent.dedupe_key,
            )
            return False

        if await self._log_repository.exists(
            intent.notification_type, intent.dedupe_key, intent.to_email
        ):
            logger.info(
                "Notification skipped (duplicate): type=%s to=%s dedupe_key=%s",
                intent.notification_type,
                intent.to_email,
                intent.dedupe_key,
            )
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
            logger.error(
                "Notification skipped: system config not found (type=%s to=%s)",
                intent.notification_type,
                intent.to_email,
            )
            return False

        gateway = EmailGatewayFactory.create(config)
        gateway_name = self._gateway_name(gateway, config)
        logger.info(
            "Sending notification: type=%s to=%s subject=%r gateway=%s",
            intent.notification_type,
            intent.to_email,
            intent.subject,
            gateway_name,
        )
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
        if result.success:
            logger.info(
                "Notification sent: type=%s to=%s subject=%r gateway=%s",
                intent.notification_type,
                intent.to_email,
                intent.subject,
                gateway_name,
            )
        else:
            logger.error(
                "Notification failed: type=%s to=%s subject=%r gateway=%s error=%s",
                intent.notification_type,
                intent.to_email,
                intent.subject,
                gateway_name,
                result.error_message,
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

    @staticmethod
    def _gateway_name(gateway: object, config: SystemConfig) -> str:
        if isinstance(gateway, SmtpEmailGateway):
            return f"smtp:{config.smtp_host}:{config.smtp_port}"
        if isinstance(gateway, LoggingEmailGateway):
            return "logging"
        return gateway.__class__.__name__

    async def get_config(self) -> SystemConfig | None:
        return await self._config_repository.get()
