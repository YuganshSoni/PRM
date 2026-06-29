from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.core.config import GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, Settings
from server.core.smtp_config_bootstrap import SmtpConfigBootstrap


def _settings(**overrides) -> Settings:
    defaults = {
        "database_url": "sqlite:///:memory:",
        "jwt_secret": "a" * 32,
        "email_enabled": False,
        "gmail_address": "",
        "gmail_app_password": "",
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.asyncio
async def test_apply_from_env_returns_false_when_gmail_not_configured():
    repo = AsyncMock()
    result = await SmtpConfigBootstrap.apply_from_env(_settings(), repo)

    assert result is False
    repo.get.assert_not_awaited()
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_from_env_warns_when_email_enabled_without_credentials():
    repo = AsyncMock()
    settings = _settings(email_enabled=True)

    with patch("server.core.smtp_config_bootstrap.logger") as logger:
        result = await SmtpConfigBootstrap.apply_from_env(settings, repo)

    assert result is False
    logger.warning.assert_called_once()
    assert "EMAIL_ENABLED=true" in logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_apply_from_env_returns_false_when_config_missing():
    repo = AsyncMock()
    repo.get.return_value = None
    settings = _settings(
        email_enabled=True,
        gmail_address="ops@example.com",
        gmail_app_password="app-pass",
    )

    result = await SmtpConfigBootstrap.apply_from_env(settings, repo)

    assert result is False
    repo.get.assert_awaited_once()
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_from_env_syncs_gmail_smtp_onto_config():
    config = MagicMock()
    repo = AsyncMock()
    repo.get.return_value = config
    settings = _settings(
        email_enabled=True,
        gmail_address="ops@example.com",
        gmail_app_password="app-pass",
    )

    with patch("server.core.smtp_config_bootstrap.logger") as logger:
        result = await SmtpConfigBootstrap.apply_from_env(settings, repo)

    assert result is True
    assert config.email_enabled is True
    assert config.smtp_host == GMAIL_SMTP_HOST
    assert config.smtp_port == GMAIL_SMTP_PORT
    assert config.smtp_username == "ops@example.com"
    assert config.smtp_password == "app-pass"
    assert config.smtp_from_email == "ops@example.com"
    repo.save.assert_awaited_once_with(config)
    logger.info.assert_called_once()
