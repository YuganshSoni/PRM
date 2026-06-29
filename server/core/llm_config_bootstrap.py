import logging

from server.core.config import Settings
from server.models.enums import LlmProvider
from server.repositories.system_config_repository import SystemConfigRepository

logger = logging.getLogger(__name__)


class LlmConfigBootstrap:
    @staticmethod
    async def apply_from_env(
        settings: Settings,
        config_repository: SystemConfigRepository,
    ) -> bool:
        api_key = settings.llm_api_key.strip()
        provider = settings.llm_provider.strip().upper()
        if not api_key and not provider:
            return False

        config = await config_repository.get()
        if config is None:
            return False

        changed = False
        if api_key and config.llm_api_key != api_key:
            config.llm_api_key = api_key
            changed = True
        if provider:
            try:
                normalized = LlmProvider(provider).value
            except ValueError:
                logger.warning(
                    "Invalid LLM_PROVIDER in .env: %s (expected GEMINI or GROQ)",
                    provider,
                )
                normalized = None
            if normalized and config.llm_provider != normalized:
                config.llm_provider = normalized
                changed = True

        if changed:
            await config_repository.save(config)

        if api_key:
            logger.info(
                "LLM config: provider=%s api_key_source=env api_key_prefix=%s... "
                "gemini_model=%s",
                config.llm_provider,
                api_key[:8],
                settings.gemini_model.strip() or "default",
            )
        return changed
