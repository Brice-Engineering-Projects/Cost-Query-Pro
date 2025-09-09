"""src/app/schemas/item.py"""

from pydantic import BaseModel, Field, ConfigDict, field_serializer, computed_field
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

    # Add a serializer for the Decimal type
    @field_serializer('unit_price')
    def serialize_unit_price(self, unit_price: Decimal) -> float:
        return float(unit_price)


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

    This model includes the project object and provides convenient access
    to commonly used project fields at the top level for simplified API responses.
    """
    project: ProjectOut

    @computed_field
    @property
    def project_name(self) -> str:
        """Project name from the associated project."""
        return self.project.project_name if self.project else None

    @computed_field
    @property
    def project_number(self) -> str:
        """Project number from the associated project."""
        return self.project.project_number if self.project else None

    @computed_field
    @property
    def state(self) -> str:
        """State code from the associated project."""
        return self.project.state if self.project else None

    @computed_field
    @property
    def year(self) -> int:
        """Project year from the associated project."""
        return self.project.year if self.project else None

