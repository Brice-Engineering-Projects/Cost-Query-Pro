"""
src/cost_query_pro/models/upload_history.py

Upload History Model:
---------------------
Enables audit trails, debugging, and UI history (admins can review past uploads).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base

if TYPE_CHECKING:
    from cost_query_pro.models.data_quality_issue import DataQualityIssue
    from cost_query_pro.models.item import Item
    from cost_query_pro.models.user import User


class UploadHistory(Base):
    __tablename__ = "upload_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(Text, default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="uploads")
    data_quality: Mapped[list[DataQualityIssue]] = relationship(
        "DataQualityIssue", back_populates="upload", cascade="all, delete-orphan"
    )
    items: Mapped[list[Item]] = relationship("Item", back_populates="upload")

    def __repr__(self) -> str:
        return (
            f"UploadHistory(id={self.id}, filename='{self.filename}', "
            f"records_inserted={self.records_inserted}, status='{self.status}', "
            f"created_at='{self.created_at}')"
        )
