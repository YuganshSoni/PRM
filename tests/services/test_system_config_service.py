from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.core.api_key_masker import ApiKeyMasker
from server.core.exceptions import (
    InvalidLlmApiKeyError,
    InvalidMaxWeeklyHoursError,
    InvalidSchedulerIntervalError,
    InvalidSmtpConfigError,
    InvalidSmtpPortError,
    LlmNotConfiguredError,
    NoConfigFieldsToUpdateError,
    SystemConfigNotFoundError,
)
from server.models.enums import LlmProvider
from server.schemas.requests.config import UpdateSystemConfigRequest
from server.services.system_config_service import LlmConfig, SystemConfigService


def _config(**overrides) -> SimpleNamespace:
    base = {
        "id": 1,
        "llm_provider": LlmProvider.GEMINI,
        "llm_api_key": "sk-test-key",
        "scheduler_interval_hours": 4,
        "max_weekly_hours": 40,
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "user",
        "smtp_password": "pass",
        "smtp_from_email": "noreply@example.com",
        "email_enabled": False,
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(repo: AsyncMock) -> SystemConfigService:
    return SystemConfigService(repo, ApiKeyMasker())


@pytest.mark.asyncio
async def test_get_config_raises_when_missing(service, repo):
    repo.get.return_value = None
    with pytest.raises(SystemConfigNotFoundError):
        await service.get_config()


@pytest.mark.asyncio
async def test_get_config_masks_secrets(service, repo):
    repo.get.return_value = _config()
    result = await service.get_config()
    assert result.llm_api_key_masked == ApiKeyMasker.MASK
    assert result.smtp_password_masked == ApiKeyMasker.MASK
    assert result.max_weekly_hours == 40


@pytest.mark.asyncio
async def test_get_llm_config_requires_api_key(service, repo):
    repo.get.return_value = _config(llm_api_key="")
    with patch(
        "server.services.system_config_service.resolve_llm_credentials",
        return_value=None,
    ):
        with pytest.raises(LlmNotConfiguredError):
            await service.get_llm_config()


@pytest.mark.asyncio
async def test_get_llm_config_happy_path(service, repo):
    repo.get.return_value = _config()
    with patch(
        "server.services.system_config_service.resolve_llm_credentials",
        return_value=(LlmProvider.GEMINI, "resolved-key"),
    ):
        result = await service.get_llm_config()
    assert result == LlmConfig(
        provider=LlmProvider.GEMINI,
        api_key="resolved-key",
        max_weekly_hours=40,
    )


@pytest.mark.asyncio
async def test_update_requires_at_least_one_field(service):
    dto = UpdateSystemConfigRequest()
    with pytest.raises(NoConfigFieldsToUpdateError):
        await service.update_config(dto)


@pytest.mark.asyncio
async def test_update_rejects_empty_llm_api_key(service, repo):
    repo.get.return_value = _config()
    dto = UpdateSystemConfigRequest(llm_api_key="   ")
    with pytest.raises(InvalidLlmApiKeyError):
        await service.update_config(dto)


@pytest.mark.asyncio
async def test_update_rejects_invalid_smtp_port(service, repo):
    repo.get.return_value = _config()
    dto = UpdateSystemConfigRequest(smtp_port=8080)
    with pytest.raises(InvalidSmtpPortError):
        await service.update_config(dto)


@pytest.mark.asyncio
async def test_update_rejects_empty_smtp_password(service, repo):
    repo.get.return_value = _config()
    dto = UpdateSystemConfigRequest(smtp_password="  ")
    with pytest.raises(InvalidSmtpConfigError, match="SMTP password"):
        await service.update_config(dto)


@pytest.mark.asyncio
async def test_enabling_email_requires_smtp_host(service, repo):
    repo.get.return_value = _config(smtp_host="", email_enabled=False)
    dto = UpdateSystemConfigRequest(email_enabled=True)
    with pytest.raises(InvalidSmtpConfigError, match="SMTP host"):
        await service.update_config(dto)


@pytest.mark.asyncio
async def test_update_saves_valid_max_weekly_hours(service, repo):
    config = _config()
    repo.get.return_value = config
    repo.save.return_value = config
    dto = UpdateSystemConfigRequest(max_weekly_hours=32)

    with patch("server.services.system_config_service.get_scheduler_manager", return_value=None):
        saved = await service.update_config(dto)

    assert saved.max_weekly_hours == 32
    repo.save.assert_awaited_once()


def test_validate_scheduler_interval_bounds(service):
    with pytest.raises(InvalidSchedulerIntervalError):
        service._validate_scheduler_interval(0)
    with pytest.raises(InvalidSchedulerIntervalError):
        service._validate_scheduler_interval(25)
    service._validate_scheduler_interval(12)


def test_validate_max_weekly_hours_bounds(service):
    with pytest.raises(InvalidMaxWeeklyHoursError):
        service._validate_max_weekly_hours(0)
    with pytest.raises(InvalidMaxWeeklyHoursError):
        service._validate_max_weekly_hours(200)
    service._validate_max_weekly_hours(40)
