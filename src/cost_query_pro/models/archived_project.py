"""
src/cost_query_pro/models/archived_project.py

Archived Project Model:
-----------------------
Stores archived project details for projects.
"""

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from cost_query_pro.db import Base

class ArchivedProject(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False, index=True)
    project_number = Column(String, unique=True, nullable=False, index=True)
    state = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    archived_at = Column(Boolean, default=False)
    purged_by_user_id = Column(Integer, nullable=True)

    # Relationship to Items
    archived_items = relationship(
        "ArchivedItem",
        back_populates="archived_project",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"ArchivedProject(id={self.id}, project_name='{self.project_name}', project_number='{self.project_number}', state='{self.state}', year={self.year}, archived_at={self.archived_at}, purged_by_user_id={self.purged_by_user_id})"
