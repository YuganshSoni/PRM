from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from server.models.employee import Employee
    from server.models.timesheet_entry import TimesheetEntry


class Timesheet(Base, CreatedAtMixin):
    __tablename__ = "timesheets"
    __table_args__ = (UniqueConstraint("employee_id", "week_start"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    week_start: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    total_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    employee: Mapped["Employee"] = relationship(back_populates="timesheets")
    entries: Mapped[list["TimesheetEntry"]] = relationship(back_populates="timesheet")
