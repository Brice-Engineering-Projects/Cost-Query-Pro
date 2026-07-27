"""
src/cost_query_pro/models/project.py

Project Model:
--------------
Stores project details for projects.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_number: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Relationship to Items
    items = relationship("Item", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"Project(id={self.id}, project_name='{self.project_name}', project_number='{self.project_number}', \n"
            f"state='{self.state}', year={self.year})"
        )
