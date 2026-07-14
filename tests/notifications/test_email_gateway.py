from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.models.system_config import SystemConfig
from server.notifications.dto.notification_dto import EmailMessage
from server.notifications.gateways.email_gateway import (
    EmailGatewayFactory,
    LoggingEmailGateway,
    SmtpEmailGateway,
    SmtpSettings,
)


def _message(**overrides) -> EmailMessage:
    base = {
        "to_email": "user@example.com",
        "subject": "Hello",
        "body": "Line one\nLine two",
    }
    base.update(overrides)
    return EmailMessage(**base)


def _smtp_settings(**overrides) -> SmtpSettings:
    base = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "smtp-user",
        "password": "smtp-pass",
        "from_email": "noreply@example.com",
    }
    base.update(overrides)
    return SmtpSettings(**base)


@pytest.mark.asyncio
async def test_logging_email_gateway_returns_success(caplog):
    gateway = LoggingEmailGateway()
    with caplog.at_level("INFO"):
        result = await gateway.send(_message())

    assert result.success is True
    assert result.error_message is None
    assert "EMAIL to=user@example.com" in caplog.text
    assert "Line one | Line two" in caplog.text


@pytest.mark.asyncio
async def test_smtp_gateway_sends_with_start_tls_on_587():
    gateway = SmtpEmailGateway(_smtp_settings(port=587))
    mock_send = AsyncMock()

    with patch(
        "aiosmtplib.send",
        new=mock_send,
    ):
        result = await gateway.send(_message())

    assert result.success is True
    mock_send.assert_awaited_once()
    kwargs = mock_send.await_args.kwargs
    assert kwargs["hostname"] == "smtp.example.com"
    assert kwargs["port"] == 587
    assert kwargs["username"] == "smtp-user"
    assert kwargs["password"] == "smtp-pass"
    assert kwargs["start_tls"] is True
    assert "use_tls" not in kwargs

    mime = mock_send.await_args.args[0]
    assert mime["From"] == "noreply@example.com"
    assert mime["To"] == "user@example.com"
    assert mime["Subject"] == "Hello"


@pytest.mark.asyncio
async def test_smtp_gateway_uses_tls_on_port_465():
    gateway = SmtpEmailGateway(_smtp_settings(port=465))
    mock_send = AsyncMock()

    with patch("aiosmtplib.send", new=mock_send):
        result = await gateway.send(_message())

    assert result.success is True
    kwargs = mock_send.await_args.kwargs
    assert kwargs["use_tls"] is True
    assert "start_tls" not in kwargs


@pytest.mark.asyncio
async def test_smtp_gateway_passes_none_for_empty_credentials():
    gateway = SmtpEmailGateway(_smtp_settings(username="", password=""))
    mock_send = AsyncMock()

    with patch("aiosmtplib.send", new=mock_send):
        await gateway.send(_message())

    kwargs = mock_send.await_args.kwargs
    assert kwargs["username"] is None
    assert kwargs["password"] is None


@pytest.mark.asyncio
async def test_smtp_gateway_returns_failure_on_exception():
    gateway = SmtpEmailGateway(_smtp_settings())

    with patch("aiosmtplib.send", new=AsyncMock(side_effect=RuntimeError("boom"))):
        result = await gateway.send(_message())

    assert result.success is False
    assert result.error_message == "boom"


def test_factory_returns_logging_for_non_system_config():
    gateway = EmailGatewayFactory.create(MagicMock())
    assert isinstance(gateway, LoggingEmailGateway)


def test_factory_returns_logging_when_email_disabled():
    config = SystemConfig(
        email_enabled=False,
        smtp_host="smtp.example.com",
        smtp_from_email="from@example.com",
    )
    gateway = EmailGatewayFactory.create(config)
    assert isinstance(gateway, LoggingEmailGateway)


def test_factory_returns_logging_when_host_blank():
    config = SystemConfig(
        email_enabled=True,
        smtp_host="   ",
        smtp_from_email="from@example.com",
    )
    gateway = EmailGatewayFactory.create(config)
    assert isinstance(gateway, LoggingEmailGateway)


def test_factory_returns_logging_when_from_email_blank():
    config = SystemConfig(
        email_enabled=True,
        smtp_host="smtp.example.com",
        smtp_from_email="  ",
    )
    gateway = EmailGatewayFactory.create(config)
    assert isinstance(gateway, LoggingEmailGateway)


def test_factory_returns_smtp_when_enabled_and_configured():
    config = SystemConfig(
        email_enabled=True,
        smtp_host=" smtp.example.com ",
        smtp_port=465,
        smtp_username=" user ",
        smtp_password=" pass ",
        smtp_from_email=" from@example.com ",
    )
    gateway = EmailGatewayFactory.create(config)
    assert isinstance(gateway, SmtpEmailGateway)
    assert gateway._settings.host == "smtp.example.com"
    assert gateway._settings.port == 465
    assert gateway._settings.username == "user"
    assert gateway._settings.password == "pass"
    assert gateway._settings.from_email == "from@example.com"
