from dataclasses import dataclass

from server.core.api_key_masker import ApiKeyMasker
from server.core.llm_config_resolver import resolve_llm_credentials
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
from server.models.system_config import SystemConfig
from server.repositories.system_config_repository import SystemConfigRepository
from server.scheduler.registry import get_scheduler_manager
from server.schemas.requests.config import UpdateSystemConfigRequest
from server.schemas.responses.config import SystemConfigResponse


@dataclass(frozen=True)
class LlmConfig:
    provider: LlmProvider
    api_key: str
    max_weekly_hours: int


class SystemConfigService:
    MIN_SCHEDULER_HOURS = 1
    MAX_SCHEDULER_HOURS = 24
    MIN_WEEKLY_HOURS = 1
    MAX_WEEKLY_HOURS = 168
    ALLOWED_SMTP_PORTS = frozenset({25, 465, 587, 2525})

    def __init__(
        self,
        config_repository: SystemConfigRepository,
        api_key_masker: ApiKeyMasker,
    ) -> None:
        self._config_repository = config_repository
        self._api_key_masker = api_key_masker

    async def get_config(self) -> SystemConfigResponse:
        config = await self._require_config()
        return self._to_response(config)

    async def get_llm_config(self) -> LlmConfig:
        config = await self._require_config()
        resolved = resolve_llm_credentials(config)
        if resolved is None:
            raise LlmNotConfiguredError("LLM API key is not configured")
        provider, api_key = resolved
        return LlmConfig(
            provider=provider,
            api_key=api_key,
            max_weekly_hours=config.max_weekly_hours,
        )

    async def update_config(self, dto: UpdateSystemConfigRequest) -> SystemConfig:
        if not dto.model_fields_set:
            raise NoConfigFieldsToUpdateError("At least one config field is required")

        config = await self._require_config()

        if "llm_api_key" in dto.model_fields_set:
            if dto.llm_api_key is None or not dto.llm_api_key.strip():
                raise InvalidLlmApiKeyError("LLM API key cannot be empty")
            config.llm_api_key = dto.llm_api_key.strip()

        if dto.llm_provider is not None:
            config.llm_provider = dto.llm_provider

        if dto.scheduler_interval_hours is not None:
            self._validate_scheduler_interval(dto.scheduler_interval_hours)
            config.scheduler_interval_hours = dto.scheduler_interval_hours

        if dto.max_weekly_hours is not None:
            self._validate_max_weekly_hours(dto.max_weekly_hours)
            config.max_weekly_hours = dto.max_weekly_hours

        if "smtp_host" in dto.model_fields_set and dto.smtp_host is not None:
            config.smtp_host = dto.smtp_host.strip()

        if dto.smtp_port is not None:
            self._validate_smtp_port(dto.smtp_port)
            config.smtp_port = dto.smtp_port

        if "smtp_username" in dto.model_fields_set and dto.smtp_username is not None:
            config.smtp_username = dto.smtp_username.strip()

        if "smtp_password" in dto.model_fields_set and dto.smtp_password is not None:
            if not dto.smtp_password.strip():
                raise InvalidSmtpConfigError("SMTP password cannot be empty")
            config.smtp_password = dto.smtp_password.strip()

        if "smtp_from_email" in dto.model_fields_set and dto.smtp_from_email is not None:
            if not dto.smtp_from_email.strip():
                raise InvalidSmtpConfigError("SMTP from email cannot be empty")
            config.smtp_from_email = dto.smtp_from_email.strip()

        if dto.email_enabled is not None:
            config.email_enabled = dto.email_enabled

        if config.email_enabled:
            self._validate_smtp_ready(config)

        saved = await self._config_repository.save(config)

        if dto.scheduler_interval_hours is not None:
            manager = get_scheduler_manager()
            if manager is not None:
                manager.reschedule(dto.scheduler_interval_hours)

        return saved

    async def _require_config(self) -> SystemConfig:
        config = await self._config_repository.get()
        if config is None:
            raise SystemConfigNotFoundError("System configuration not found")
        return config

    def _to_response(self, config: SystemConfig) -> SystemConfigResponse:
        return SystemConfigResponse(
            llm_provider=LlmProvider(config.llm_provider),
            llm_api_key_masked=self._api_key_masker.mask(config.llm_api_key),
            scheduler_interval_hours=config.scheduler_interval_hours,
            max_weekly_hours=config.max_weekly_hours,
            email_enabled=config.email_enabled,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_username=config.smtp_username,
            smtp_password_masked=self._api_key_masker.mask(config.smtp_password),
            smtp_from_email=config.smtp_from_email,
            updated_at=config.updated_at,
        )

    def _validate_scheduler_interval(self, hours: int) -> None:
        if hours < self.MIN_SCHEDULER_HOURS or hours > self.MAX_SCHEDULER_HOURS:
            raise InvalidSchedulerIntervalError(
                "Scheduler interval must be between 1 and 24 hours"
            )

    def _validate_max_weekly_hours(self, hours: int) -> None:
        if hours < self.MIN_WEEKLY_HOURS or hours > self.MAX_WEEKLY_HOURS:
            raise InvalidMaxWeeklyHoursError(
                "Max weekly hours must be between 1 and 168"
            )

    def _validate_smtp_port(self, port: int) -> None:
        if port not in self.ALLOWED_SMTP_PORTS:
            raise InvalidSmtpPortError(
                "SMTP port must be one of: 25, 465, 587, 2525"
            )

    def _validate_smtp_ready(self, config: SystemConfig) -> None:
        if not config.smtp_host.strip():
            raise InvalidSmtpConfigError(
                "SMTP host is required when email is enabled"
            )
        if not config.smtp_from_email.strip():
            raise InvalidSmtpConfigError(
                "SMTP from email is required when email is enabled"
            )
        self._validate_smtp_port(config.smtp_port)
