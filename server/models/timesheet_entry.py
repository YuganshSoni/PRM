from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from server.models.project import Project
    from server.models.timesheet import Timesheet
    from server.models.timesheet_entry_tag import TimesheetEntryTag


class TimesheetEntry(Base, CreatedAtMixin):
    __tablename__ = "timesheet_entries"
    __table_args__ = (
        UniqueConstraint("timesheet_id", "project_id"),
        CheckConstraint("hours >= 0", name="ck_timesheet_entries_hours"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timesheet_id: Mapped[int] = mapped_column(
        ForeignKey("timesheets.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    hours: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    timesheet: Mapped["Timesheet"] = relationship(back_populates="entries")
    project: Mapped["Project"] = relationship(back_populates="timesheet_entries")
    tags: Mapped[list["TimesheetEntryTag"]] = relationship(back_populates="entry")
