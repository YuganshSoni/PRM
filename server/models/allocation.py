from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.employee import Employee
    from server.models.project import Project


class Allocation(Base, TimestampMixin):
    __tablename__ = "allocations"
    __table_args__ = (
        CheckConstraint("from_date < to_date", name="ck_allocations_dates"),
        CheckConstraint(
            "utilisation_percent >= 1 AND utilisation_percent <= 100",
            name="ck_allocations_utilisation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    utilisation_percent: Mapped[int] = mapped_column(Integer)
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date] = mapped_column(Date)

    employee: Mapped["Employee"] = relationship(back_populates="allocations")
    project: Mapped["Project"] = relationship(back_populates="allocations")
