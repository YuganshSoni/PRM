from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from server.models.base import Base
from server.models.enums import LlmProvider


class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    llm_provider: Mapped[str] = mapped_column(String(20), default=LlmProvider.GEMINI)
    llm_api_key: Mapped[str] = mapped_column(String(500), default="")
    scheduler_interval_hours: Mapped[int] = mapped_column(Integer, default=4)
    max_weekly_hours: Mapped[int] = mapped_column(Integer, default=40)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
