import logging

from server.core.config import Settings
from server.repositories.system_config_repository import SystemConfigRepository

logger = logging.getLogger(__name__)


class SmtpConfigBootstrap:
    @staticmethod
    async def apply_from_env(
        settings: Settings,
        config_repository: SystemConfigRepository,
    ) -> bool:
        gmail_smtp = settings.resolve_gmail_smtp()
        if gmail_smtp is None:
            if settings.email_enabled:
                logger.warning(
                    "EMAIL_ENABLED=true but GMAIL_ADDRESS or GMAIL_APP_PASSWORD "
                    "is missing — emails will not send until both are set in .env"
                )
            return False

        config = await config_repository.get()
        if config is None:
            return False

        config.email_enabled = gmail_smtp.email_enabled
        config.smtp_host = gmail_smtp.smtp_host
        config.smtp_port = gmail_smtp.smtp_port
        config.smtp_username = gmail_smtp.smtp_username
        config.smtp_password = gmail_smtp.smtp_password
        config.smtp_from_email = gmail_smtp.smtp_from_email
        await config_repository.save(config)
        logger.info(
            "Gmail SMTP synced from environment (from=%s host=%s port=%s)",
            config.smtp_from_email,
            config.smtp_host,
            config.smtp_port,
        )
        return True
