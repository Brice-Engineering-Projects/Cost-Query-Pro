"""
src/cost_query_pro/models/upload_history.py

Upload History Model:
---------------------
Enables audit trails, debugging, and UI history (admins can review past uploads.
"""

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, Text, func)
from sqlalchemy.orm import relationship

from cost_query_pro.db import Base


class UploadHistory(Base):
    __tablename__ = "upload_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(Text, nullable=False)
    records_inserted = Column(Integer, default=0)
    status = Column(Text, default="success")
    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="uploads")
    data_quality = relationship(
        "DataQualityIssue", back_populates="upload", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"UploadHistory(id={self.id}, filename='{self.filename}', records_inserted={self.records_inserted}, status='{self.status}', created_at='{self.created_at}')"
