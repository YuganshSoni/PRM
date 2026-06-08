from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin
from server.models.enums import EmployeeStatus

if TYPE_CHECKING:
    from server.models.allocation import Allocation
    from server.models.employee_skill import EmployeeSkill
    from server.models.project import Project
    from server.models.timesheet import Timesheet
    from server.models.user import User


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True
    )
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(100), index=True)
    designation: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(
        String(20), default=EmployeeStatus.BENCH, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    user: Mapped["User"] = relationship(back_populates="employee")
    skills: Mapped[list["EmployeeSkill"]] = relationship(back_populates="employee")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="employee")
    timesheets: Mapped[list["Timesheet"]] = relationship(back_populates="employee")
    managed_projects: Mapped[list["Project"]] = relationship(back_populates="manager")
