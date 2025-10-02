"""src/cost_query_pro/models/item.py"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from cost_query_pro.db import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    item_description = Column(String, nullable=False, index=True)
    unit = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)

    # Relationship to Project
    project = relationship(
        "Project",
        back_populates="items"
    )
