"""
src/cost_query_pro/models/data_quality_issue.py

Data Quality Issue Model:
-------------------------
Logging any failed or partial uploads (bad formatting, invalid data). Helps detect patterns of data issues — e.g.,
recurring format problems from certain agencies.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from cost_query_pro.db import Base


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    issue_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    # Relationship to Upload model
    upload = relationship("Upload", back_populates="data_quality_issues")

    def __repr__(self):
        return (
            f"<DataQualityIssue(id={self.id}, upload_id={self.upload_id}, issue_type='{self.issue_type}', \n"
            f"description='{self.description}', timestamp='{self.timestamp}')>"
        )
