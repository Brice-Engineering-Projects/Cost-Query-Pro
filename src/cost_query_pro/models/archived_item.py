"""Archived item model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base

if TYPE_CHECKING:
    from cost_query_pro.models.archived_project import ArchivedProject
    from cost_query_pro.models.upload_history import UploadHistory


class ArchivedItem(Base):
    """Stores archived item details for projects."""

    __tablename__ = "archived_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("archived_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_description: Mapped[str] = mapped_column(String, nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("upload_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to Project
    archived_project: Mapped[ArchivedProject] = relationship(
        "ArchivedProject", back_populates="archived_items"
    )
    upload: Mapped[Optional[UploadHistory]] = relationship("UploadHistory")

    def __repr__(self) -> str:
        return (
            f"ArchivedItem(id={self.id}, project_id={self.project_id}, "
            f"item_description='{self.item_description}', unit='{self.unit}', "
            f"unit_price={self.unit_price}, quantity={self.quantity}, "
            f"upload_id={self.upload_id}, archived_at={self.archived_at})"
        )
