"""
src/cost_query_pro/models/archived_item.py

Item Model
-----------
Stores archived item details for projects.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from cost_query_pro.db import Base


class ArchivedItem(Base):
    """Stores archived item details for projects."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    item_description = Column(String, nullable=False, index=True)
    unit = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

    # Relationship to Project
    archived_project = relationship("ArchivedProject", back_populates="archived_items")

    def __repr__(self) -> str:
        return (
            f"ArchivedItem(id={self.id}, project_id={self.project_id}, item_description='{self.item_description}', \n"
            f"unit='{self.unit}', unit_price={self.unit_price}, quantity={self.quantity})"
        )
