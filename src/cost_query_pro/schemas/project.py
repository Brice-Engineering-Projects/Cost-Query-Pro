"""src/cost_query_pro/schemas/project.py"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    """
    Base Project schema with shared attributes.
    """

    project_name: str = Field(
        ..., min_length=1, max_length=255, example="Main St. Sewer Rehab"
    )
    project_number: str = Field(..., min_length=1, max_length=50, example="202301")
    state: str = Field(..., min_length=2, max_length=2, example="FL")
    year: int = Field(..., ge=1900, le=2100, example=2023)

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(ProjectBase):
    """
    Schema for creating a new project.
    """


class ProjectUpdate(BaseModel):
    """
    Schema for updating an existing project.
    All fields optional for PATCH semantics.
    """

    project_name: Optional[str] = Field(
        None, min_length=1, max_length=255, example="Main St. Sewer Rehab"
    )
    project_number: Optional[str] = Field(
        None, min_length=1, max_length=50, example="202301"
    )
    state: Optional[str] = Field(None, min_length=2, max_length=2, example="FL")
    year: Optional[int] = Field(None, ge=1900, le=2100, example=2023)

    model_config = ConfigDict(from_attributes=True)


class ProjectOut(ProjectBase):
    """
    Schema for project responses.
    """

    id: int
