"""app/schemas/project.py"""

from pydantic import BaseModel
from typing import List, Optional

class ItemBase(BaseModel):
    item_description: str
    unit: str
    unit_price: float

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int

    class Config:
        orm_mode = True


class ProjectBase(BaseModel):
    project_name: str
    project_number: str
    state: str
    year: int

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    items: Optional[List[Item]] = []
"""app/schemas/project.py"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProjectBase(BaseModel):
    """Base Project schema with common attributes"""
    project_name: str
    project_number: str
    state: str
    year: int

class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""
    pass

class ProjectUpdate(BaseModel):
    """Schema for updating an existing project"""
    project_name: Optional[str] = None
    project_number: Optional[str] = None
    state: Optional[str] = None
    year: Optional[int] = None

class ProjectOut(ProjectBase):
    """Schema for project responses"""
    id: int

    class Config:
        orm_mode = True
    class Config:
        orm_mode = True
