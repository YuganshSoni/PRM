from unittest.mock import MagicMock, patch

import pytest

from server.core.llm_config_resolver import resolve_llm_credentials
from server.models.enums import LlmProvider


def _db_config(*, provider: str = "GEMINI", api_key: str = "") -> MagicMock:
    config = MagicMock()
    config.llm_provider = provider
    config.llm_api_key = api_key
    return config


def test_resolve_prefers_settings_api_key_and_provider():
    settings = MagicMock(
        llm_api_key=" env-key ",
        llm_provider="groq",
    )
    with patch(
        "server.core.llm_config_resolver.get_settings",
        return_value=settings,
    ):
        result = resolve_llm_credentials(
            _db_config(provider="GEMINI", api_key="db-key")
        )

    assert result == (LlmProvider.GROQ, "env-key")


def test_resolve_falls_back_to_db_credentials():
    settings = MagicMock(llm_api_key="", llm_provider="")
    with patch(
        "server.core.llm_config_resolver.get_settings",
        return_value=settings,
    ):
        result = resolve_llm_credentials(
            _db_config(provider="GEMINI", api_key="  db-secret  ")
        )

    assert result == (LlmProvider.GEMINI, "db-secret")


def test_resolve_returns_none_when_no_api_key():
    settings = MagicMock(llm_api_key="  ", llm_provider="GEMINI")
    with patch(
        "server.core.llm_config_resolver.get_settings",
        return_value=settings,
    ):
        result = resolve_llm_credentials(_db_config(api_key=""))

    assert result is None


def test_resolve_uses_settings_provider_with_db_key():
    settings = MagicMock(llm_api_key="", llm_provider="GROQ")
    with patch(
        "server.core.llm_config_resolver.get_settings",
        return_value=settings,
    ):
        result = resolve_llm_credentials(
            _db_config(provider="GEMINI", api_key="db-key")
        )

    assert result == (LlmProvider.GROQ, "db-key")


def test_resolve_rejects_unknown_provider():
    settings = MagicMock(llm_api_key="key", llm_provider="UNKNOWN")
    with patch(
        "server.core.llm_config_resolver.get_settings",
        return_value=settings,
    ):
        with pytest.raises(ValueError):
            resolve_llm_credentials(_db_config())
