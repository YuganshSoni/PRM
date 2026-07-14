from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.core.config import Settings
from server.core.llm_config_bootstrap import LlmConfigBootstrap


def _settings(**overrides) -> Settings:
    defaults = {
        "database_url": "sqlite:///:memory:",
        "jwt_secret": "a" * 32,
        "llm_provider": "",
        "llm_api_key": "",
        "gemini_model": "",
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.asyncio
async def test_apply_from_env_returns_false_when_env_empty():
    repo = AsyncMock()
    result = await LlmConfigBootstrap.apply_from_env(_settings(), repo)
    assert result is False
    repo.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_from_env_returns_false_when_config_missing():
    repo = AsyncMock()
    repo.get.return_value = None
    result = await LlmConfigBootstrap.apply_from_env(
        _settings(llm_api_key="secret-key"),
        repo,
    )
    assert result is False
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_from_env_updates_api_key_and_provider():
    config = MagicMock()
    config.llm_api_key = "old"
    config.llm_provider = "GEMINI"
    repo = AsyncMock()
    repo.get.return_value = config

    with patch("server.core.llm_config_bootstrap.logger") as logger:
        result = await LlmConfigBootstrap.apply_from_env(
            _settings(llm_api_key="new-secret", llm_provider="groq", gemini_model="m1"),
            repo,
        )

    assert result is True
    assert config.llm_api_key == "new-secret"
    assert config.llm_provider == "GROQ"
    repo.save.assert_awaited_once_with(config)
    logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_apply_from_env_ignores_invalid_provider():
    config = MagicMock()
    config.llm_api_key = "same"
    config.llm_provider = "GEMINI"
    repo = AsyncMock()
    repo.get.return_value = config

    with patch("server.core.llm_config_bootstrap.logger") as logger:
        result = await LlmConfigBootstrap.apply_from_env(
            _settings(llm_api_key="same", llm_provider="OPENAI"),
            repo,
        )

    assert result is False
    repo.save.assert_not_awaited()
    logger.warning.assert_called_once()
    assert "Invalid LLM_PROVIDER" in logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_apply_from_env_provider_only_when_changed():
    config = MagicMock()
    config.llm_api_key = ""
    config.llm_provider = "GEMINI"
    repo = AsyncMock()
    repo.get.return_value = config

    result = await LlmConfigBootstrap.apply_from_env(
        _settings(llm_provider="GROQ"),
        repo,
    )

    assert result is True
    assert config.llm_provider == "GROQ"
    repo.save.assert_awaited_once_with(config)
