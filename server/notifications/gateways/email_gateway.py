import logging
from dataclasses import dataclass

from server.notifications.dto.notification_dto import EmailMessage, SendResult

logger = logging.getLogger(__name__)


class LoggingEmailGateway:
    async def send(self, message: EmailMessage) -> SendResult:
        logger.info(
            "EMAIL to=%s subject=%s body=%s",
            message.to_email,
            message.subject,
            message.body.replace("\n", " | "),
        )
        return SendResult(success=True)


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    username: str
    password: str
    from_email: str


class SmtpEmailGateway:
    def __init__(self, settings: SmtpSettings) -> None:
        self._settings = settings

    async def send(self, message: EmailMessage) -> SendResult:
        try:
            import aiosmtplib
            from email.message import EmailMessage as MimeMessage

            mime = MimeMessage()
            mime["From"] = self._settings.from_email
            mime["To"] = message.to_email
            mime["Subject"] = message.subject
            mime.set_content(message.body)

            tls_kwargs = (
                {"use_tls": True}
                if self._settings.port == 465
                else {"start_tls": True}
            )
            await aiosmtplib.send(
                mime,
                hostname=self._settings.host,
                port=self._settings.port,
                username=self._settings.username or None,
                password=self._settings.password or None,
                **tls_kwargs,
            )
            logger.info(
                "SMTP delivered: host=%s port=%s from=%s to=%s subject=%r",
                self._settings.host,
                self._settings.port,
                self._settings.from_email,
                message.to_email,
                message.subject,
            )
            return SendResult(success=True)
        except Exception as exc:
            logger.error(
                "SMTP delivery failed: host=%s port=%s to=%s subject=%r error=%s",
                self._settings.host,
                self._settings.port,
                message.to_email,
                message.subject,
                exc,
            )
            return SendResult(success=False, error_message=str(exc))


class EmailGatewayFactory:
    @staticmethod
    def create(config):
        from server.models.system_config import SystemConfig

        if not isinstance(config, SystemConfig):
            return LoggingEmailGateway()
        if (
            config.email_enabled
            and config.smtp_host.strip()
            and config.smtp_from_email.strip()
        ):
            return SmtpEmailGateway(
                SmtpSettings(
                    host=config.smtp_host.strip(),
                    port=config.smtp_port,
                    username=config.smtp_username.strip(),
                    password=config.smtp_password.strip(),
                    from_email=config.smtp_from_email.strip(),
                )
            )
        return LoggingEmailGateway()
