import os
from unittest.mock import patch

from server.core.config import (
    GMAIL_SMTP_HOST,
    GMAIL_SMTP_PORT,
    Settings,
    get_settings,
)


def _settings(**overrides) -> Settings:
    """Build Settings without reading project .env / host env Gmail values."""
    defaults = {
        "database_url": "sqlite:///:memory:",
        "jwt_secret": "a" * 32,
        "email_enabled": False,
        "gmail_address": "",
        "gmail_app_password": "",
        "cors_origins": "",
    }
    defaults.update(overrides)
    env = {
        "DATABASE_URL": str(defaults["database_url"]),
        "JWT_SECRET": str(defaults["jwt_secret"]),
        "EMAIL_ENABLED": str(defaults["email_enabled"]).lower(),
        "GMAIL_ADDRESS": str(defaults["gmail_address"]),
        "GMAIL_APP_PASSWORD": str(defaults["gmail_app_password"]),
        "CORS_ORIGINS": str(defaults["cors_origins"]),
    }
    with patch.dict(os.environ, env, clear=False):
        return Settings(_env_file=None, **defaults)


def test_resolve_gmail_smtp_returns_none_without_credentials():
    assert _settings().resolve_gmail_smtp() is None
    assert (
        _settings(gmail_address="ops@example.com").resolve_gmail_smtp() is None
    )
    assert _settings(gmail_app_password="secret").resolve_gmail_smtp() is None


def test_resolve_gmail_smtp_builds_settings():
    smtp = _settings(
        email_enabled=True,
        gmail_address="  ops@example.com ",
        gmail_app_password=" app-pass ",
    ).resolve_gmail_smtp()

    assert smtp is not None
    assert smtp.email_enabled is True
    assert smtp.smtp_host == GMAIL_SMTP_HOST
    assert smtp.smtp_port == GMAIL_SMTP_PORT
    assert smtp.smtp_username == "ops@example.com"
    assert smtp.smtp_password == "app-pass"
    assert smtp.smtp_from_email == "ops@example.com"


def test_cors_origin_list_parses_comma_separated_values():
    settings = _settings(cors_origins=" http://a.com ,http://b.com, , ")
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]


def test_cors_origin_list_empty_when_blank():
    assert _settings(cors_origins="").cors_origin_list == []
    assert _settings(cors_origins="   ").cors_origin_list == []


def test_warn_short_jwt_secret():
    with patch("server.core.config.logger") as logger:
        _settings(jwt_secret="short", jwt_secret_min_length=32)
    logger.warning.assert_called_once()


def test_get_settings_is_cached():
    get_settings.cache_clear()
    with patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "sqlite:///:memory:",
            "JWT_SECRET": "b" * 32,
        },
        clear=False,
    ):
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()
    assert first is second
    get_settings.cache_clear()
