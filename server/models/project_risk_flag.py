from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

if TYPE_CHECKING:
    from server.models.project_health import ProjectHealth


class ProjectRiskFlag(Base):
    __tablename__ = "project_risk_flags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_health_id: Mapped[int] = mapped_column(
        ForeignKey("project_health.id", ondelete="CASCADE"), index=True
    )
    flag_text: Mapped[str] = mapped_column(Text)
    is_positive: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project_health: Mapped["ProjectHealth"] = relationship(
        back_populates="risk_flags"
    )
