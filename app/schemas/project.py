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

    class Config:
        orm_mode = True
