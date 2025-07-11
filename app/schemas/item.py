"""app/schemas/item.py"""

from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.project import ProjectOut

class ItemBase(BaseModel):
    """Base Item schema with common attributes"""
    item_description: str
    unit: str
    unit_price: float

class ItemCreate(ItemBase):
    """Schema for creating a new item"""
    project_id: int

class ItemUpdate(BaseModel):
    """Schema for updating an existing item"""
    item_description: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    project_id: Optional[int] = None

class ItemOut(ItemBase):
    """Schema for item responses"""
    id: int
    project_id: int

    class Config:
        orm_mode = True

class ItemWithProject(ItemOut):
    """Schema for item responses with project details"""
    project: ProjectOut

    class Config:
        orm_mode = True
