from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

if TYPE_CHECKING:
    from server.models.project import Project
    from server.models.project_risk_flag import ProjectRiskFlag


class ProjectHealth(Base):
    __tablename__ = "project_health"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True
    )
    health_status: Mapped[str] = mapped_column(String(20), index=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="health")
    risk_flags: Mapped[list["ProjectRiskFlag"]] = relationship(
        back_populates="project_health"
    )
