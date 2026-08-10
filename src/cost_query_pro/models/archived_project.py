"""Archived project model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base

if TYPE_CHECKING:
    from cost_query_pro.models.archived_item import ArchivedItem
    from cost_query_pro.models.user import User


class ArchivedProject(Base):
    __tablename__ = "archived_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    purged_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationship to Items
    archived_items: Mapped[list[ArchivedItem]] = relationship(
        "ArchivedItem", back_populates="archived_project", cascade="all, delete-orphan"
    )
    purged_by: Mapped[Optional[User]] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"ArchivedProject(id={self.id}, project_name='{self.project_name}', "
            f"project_number='{self.project_number}', state='{self.state}', "
            f"year={self.year}, archived_at={self.archived_at}, "
            f"purged_by_user_id={self.purged_by_user_id})"
        )
