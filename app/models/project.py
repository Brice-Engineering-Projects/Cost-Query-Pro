"""app/models/project.py"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False)
    project_number = Column(String, unique=True, nullable=False)
    state = Column(String, nullable=False)
    year = Column(Integer, nullable=False)

    # Relationship to Items
    items = relationship("Item", back_populates="project", cascade="all, delete-orphan")
