from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.models.resource import Resource



class Designation(Base):
    __tablename__ = "designations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    resources: Mapped[list["Resource"]] = relationship(back_populates="designation")
