"""src/app/schemas/item.py"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from decimal import Decimal
from src.app.schemas.project import ProjectOut

class ItemBase(BaseModel):
    """
    Base schema for Item shared attributes.
    """
    item_description: str = Field(..., min_length=1, max_length=255, example='8" PVC Gravity Sewer')
    unit: str = Field(..., min_length=1, max_length=50, example='LF')
    unit_price: Decimal = Field(..., example=45.32)

    model_config = ConfigDict(from_attributes=True)


class ItemCreate(ItemBase):
    """
    Schema for creating a new item.
    """
    project_id: int = Field(..., example=1)


class ItemUpdate(BaseModel):
    """
    Schema for updating an existing item.
    All fields optional for PATCH semantics.
    """
    item_description: Optional[str] = Field(None, min_length=1, max_length=255, example='8" PVC Gravity Sewer')
    unit: Optional[str] = Field(None, min_length=1, max_length=50, example='LF')
    unit_price: float = Field(None, example=45.32)
    project_id: Optional[int] = Field(None, example=1)

    model_config = ConfigDict(from_attributes=True)


class ItemOut(ItemBase):
    """
    Schema for item responses.
    """
    id: int
    project_id: int


class ItemWithProject(ItemOut):
    """
    Schema for item responses with project details.
    """
    project: ProjectOut
