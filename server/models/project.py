from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.allocation import Allocation
    from server.models.milestone import Milestone
    from server.models.project_health import ProjectHealth
    from server.models.resource import Resource
    from server.models.timesheet_entry import TimesheetEntry


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="RESTRICT"), index=True
    )
    total_story_points: Mapped[int] = mapped_column(Integer, default=0)

    manager: Mapped["Resource"] = relationship(back_populates="managed_projects")
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="project")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="project")
    timesheet_entries: Mapped[list["TimesheetEntry"]] = relationship(
        back_populates="project"
    )
    health: Mapped["ProjectHealth | None"] = relationship(back_populates="project")
