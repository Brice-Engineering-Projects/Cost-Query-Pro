"""app/models/item.py"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    item_description = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)

    # Relationship to Project
    project = relationship("Project", back_populates="items")
