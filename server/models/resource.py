from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.allocation import Allocation
    from server.models.department import Department
    from server.models.designation import Designation
    from server.models.project import Project
    from server.models.resource_skill import ResourceSkill
    from server.models.resource_status import ResourceStatus
    from server.models.timesheet import Timesheet
    from server.models.user import User


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designations.id", ondelete="RESTRICT"), index=True
    )
    resource_status_id: Mapped[int] = mapped_column(
        ForeignKey("resource_statuses.id", ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("resources.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped["User"] = relationship(back_populates="resource")
    department: Mapped["Department"] = relationship(back_populates="resources")
    designation: Mapped["Designation"] = relationship(back_populates="resources")
    resource_status: Mapped["ResourceStatus"] = relationship(back_populates="resources")
    
    manager: Mapped["Resource | None"] = relationship(
        "Resource",
        remote_side="Resource.id",
        foreign_keys=[manager_id],
        back_populates="direct_reports",
    )
    direct_reports: Mapped[list["Resource"]] = relationship(
        "Resource",
        back_populates="manager",
        foreign_keys=[manager_id],
    )
    skills: Mapped[list["ResourceSkill"]] = relationship(back_populates="resource", cascade="all, delete-orphan")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="resource")
    timesheets: Mapped[list["Timesheet"]] = relationship(back_populates="resource")
    managed_projects: Mapped[list["Project"]] = relationship(back_populates="manager")
