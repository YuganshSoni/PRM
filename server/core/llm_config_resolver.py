from server.core.config import get_settings
from server.models.enums import LlmProvider
from server.models.system_config import SystemConfig


def resolve_llm_credentials(
    db_config: SystemConfig,
) -> tuple[LlmProvider, str] | None:
    settings = get_settings()
    api_key = (settings.llm_api_key or db_config.llm_api_key).strip()
    if not api_key:
        return None
    provider_raw = (settings.llm_provider or db_config.llm_provider).strip()
    return LlmProvider(provider_raw), api_key
