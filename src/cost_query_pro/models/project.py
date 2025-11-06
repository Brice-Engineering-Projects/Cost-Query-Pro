"""
src/cost_query_pro/models/project.py

Project Model:
--------------
Stores project details for projects.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from cost_query_pro.db import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False, index=True)
    project_number = Column(String, unique=True, nullable=False, index=True)
    state = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)

    # Relationship to Items
    items = relationship("Item", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Project(id={self.id}, project_name='{self.project_name}', project_number='{self.project_number}', state='{self.state}', year={self.year})"
