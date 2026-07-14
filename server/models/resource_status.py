from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.models.resource import Resource



class ResourceStatus(Base):
    __tablename__ = "resource_statuses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    resources: Mapped[list["Resource"]] = relationship(back_populates="resource_status")
