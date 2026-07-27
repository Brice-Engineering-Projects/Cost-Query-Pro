"""
src/cost_query_pro/models/data_quality_issue.py

Data Quality Issue Model:
-------------------------
Logging any failed or partial uploads (bad formatting, invalid data). Helps detect patterns of data
issues — e.g., recurring format problems from certain agencies.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base

if TYPE_CHECKING:
    from cost_query_pro.models.upload_history import UploadHistory


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("upload_history.id"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    upload: Mapped[UploadHistory] = relationship(
        "UploadHistory", back_populates="data_quality"
    )

    def __repr__(self) -> str:
        return (
            f"<DataQualityIssue(id={self.id}, upload_id={self.upload_id}, "
            f"row_number={self.row_number}, issue_type='{self.issue_type}', "
            f"description='{self.description}', timestamp='{self.timestamp}')>"
        )
