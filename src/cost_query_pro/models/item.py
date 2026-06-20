"""
src/cost_query_pro/models/item.py

Item Model
-----------
Stores item details for projects.
"""

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="ck_items_unit_price_non_negative"),
        CheckConstraint("quantity >= 0", name="ck_items_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    item_description: Mapped[str] = mapped_column(String, nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationship to Project
    project = relationship("Project", back_populates="items")

    def __repr__(self):
        return (
            f"Item(id={self.id}, project_id={self.project_id}, item_description='{self.item_description}', \n"
            f"unit='{self.unit}', unit_price={self.unit_price}, quantity={self.quantity})"
        )
