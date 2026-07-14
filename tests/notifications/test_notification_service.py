from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.models.enums import NotificationDeliveryStatus, NotificationType
from server.models.notification_log import NotificationLog
from server.models.system_config import SystemConfig
from server.notifications.dto.notification_dto import NotificationIntent, SendResult
from server.notifications.gateways.email_gateway import (
    LoggingEmailGateway,
    SmtpEmailGateway,
    SmtpSettings,
)
from server.notifications.services.notification_service import NotificationService


def _intent(**overrides) -> NotificationIntent:
    base = {
        "notification_type": NotificationType.ALLOCATION_CONFIRMATION,
        "dedupe_key": "allocation:1:confirmation",
        "to_email": "user@example.com",
        "subject": "Subject",
        "body": "Body",
        "entity_type": "allocation",
        "entity_id": 1,
    }
    base.update(overrides)
    return NotificationIntent(**base)


def _smtp_config(**overrides) -> SystemConfig:
    base = dict(
        email_enabled=True,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="user",
        smtp_password="pass",
        smtp_from_email="from@example.com",
    )
    base.update(overrides)
    return SystemConfig(**base)


def _service():
    config_repo = AsyncMock()
    log_repo = AsyncMock()
    return NotificationService(config_repo, log_repo), config_repo, log_repo


@pytest.mark.asyncio
async def test_send_skips_empty_email():
    service, config_repo, log_repo = _service()

    result = await service.send(_intent(to_email="   "))

    assert result is False
    config_repo.get.assert_not_awaited()
    log_repo.exists.assert_not_awaited()
    log_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_skips_duplicate_and_logs():
    service, config_repo, log_repo = _service()
    log_repo.exists.return_value = True

    result = await service.send(_intent())

    assert result is False
    config_repo.get.assert_not_awaited()
    log_repo.save.assert_awaited_once()
    saved: NotificationLog = log_repo.save.await_args.args[0]
    assert saved.status == NotificationDeliveryStatus.SKIPPED_DUPLICATE
    assert saved.recipient_email == "user@example.com"
    assert saved.dedupe_key == "allocation:1:confirmation"


@pytest.mark.asyncio
async def test_send_skips_when_config_missing():
    service, config_repo, log_repo = _service()
    log_repo.exists.return_value = False
    config_repo.get.return_value = None

    result = await service.send(_intent())

    assert result is False
    log_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_smtp_success():
    service, config_repo, log_repo = _service()
    log_repo.exists.return_value = False
    config_repo.get.return_value = _smtp_config()

    with patch(
        "server.notifications.services.notification_service.EmailGatewayFactory.create"
    ) as create:
        gateway = AsyncMock(spec=SmtpEmailGateway)
        gateway.send.return_value = SendResult(success=True)
        create.return_value = gateway

        # isinstance checks in _gateway_name need real type
        with patch.object(
            NotificationService,
            "_gateway_name",
            return_value="smtp:smtp.example.com:587",
        ):
            result = await service.send(_intent())

    assert result is True
    gateway.send.assert_awaited_once()
    message = gateway.send.await_args.args[0]
    assert message.to_email == "user@example.com"
    assert message.subject == "Subject"
    assert message.body == "Body"

    saved: NotificationLog = log_repo.save.await_args.args[0]
    assert saved.status == NotificationDeliveryStatus.SENT
    assert saved.error_message is None


@pytest.mark.asyncio
async def test_send_smtp_failure():
    service, config_repo, log_repo = _service()
    log_repo.exists.return_value = False
    config_repo.get.return_value = _smtp_config()

    with patch(
        "server.notifications.services.notification_service.EmailGatewayFactory.create"
    ) as create:
        gateway = MagicMock(spec=SmtpEmailGateway)
        gateway.send = AsyncMock(
            return_value=SendResult(success=False, error_message="smtp down")
        )
        create.return_value = gateway

        with patch.object(NotificationService, "_gateway_name", return_value="smtp"):
            result = await service.send(_intent())

    assert result is False
    saved: NotificationLog = log_repo.save.await_args.args[0]
    assert saved.status == NotificationDeliveryStatus.FAILED
    assert saved.error_message == "smtp down"


@pytest.mark.asyncio
async def test_send_uses_logging_gateway_when_email_disabled():
    service, config_repo, log_repo = _service()
    log_repo.exists.return_value = False
    config_repo.get.return_value = SystemConfig(
        email_enabled=False,
        smtp_host="",
        smtp_from_email="",
    )

    result = await service.send(_intent())

    assert result is True
    saved: NotificationLog = log_repo.save.await_args.args[0]
    assert saved.status == NotificationDeliveryStatus.SENT


@pytest.mark.asyncio
async def test_gateway_name_for_smtp_and_logging():
    config = _smtp_config()
    smtp = SmtpEmailGateway(
        SmtpSettings(
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            from_email=config.smtp_from_email,
        )
    )
    assert (
        NotificationService._gateway_name(smtp, config)
        == "smtp:smtp.example.com:587"
    )
    assert NotificationService._gateway_name(LoggingEmailGateway(), config) == "logging"
    assert NotificationService._gateway_name(object(), config) == "object"


@pytest.mark.asyncio
async def test_get_config_delegates_to_repository():
    service, config_repo, _log_repo = _service()
    config = _smtp_config()
    config_repo.get.return_value = config

    assert await service.get_config() is config
    config_repo.get.assert_awaited_once()
