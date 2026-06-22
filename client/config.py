from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientSettings(BaseSettings):
    api_base_url: str = "http://localhost:8000"
    request_timeout_seconds: float = 30.0
    ai_request_timeout_seconds: float = 90.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_client_settings() -> ClientSettings:
    return ClientSettings()
