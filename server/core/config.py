from dataclasses import dataclass
from functools import lru_cache
import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


@dataclass(frozen=True)
class GmailSmtpSettings:
    email_enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str


class Settings(BaseSettings):
    database_url: str
    database_echo: bool = False
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    scheduler_enabled: bool = True
    cors_origins: str = ""
    log_format: str = "text"
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    rate_limit_ai_per_minute: int = 20
    jwt_secret_min_length: int = 32
    llm_provider: str = ""
    llm_api_key: str = ""
    gemini_model: str = ""
    groq_model: str = ""
    email_enabled: bool = False
    gmail_address: str = ""
    gmail_app_password: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def warn_short_jwt_secret(self) -> "Settings":
        if len(self.jwt_secret) < self.jwt_secret_min_length:
            logger.warning(
                "JWT secret is shorter than %s bytes — use a stronger secret in production.",
                self.jwt_secret_min_length,
            )
        return self

    def resolve_gmail_smtp(self) -> GmailSmtpSettings | None:
        address = self.gmail_address.strip()
        app_password = self.gmail_app_password.strip()
        if not address or not app_password:
            return None
        return GmailSmtpSettings(
            email_enabled=self.email_enabled,
            smtp_host=GMAIL_SMTP_HOST,
            smtp_port=GMAIL_SMTP_PORT,
            smtp_username=address,
            smtp_password=app_password,
            smtp_from_email=address,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
