"""src/app/api/projects.py"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from src.app.db.session import get_db
from src.app.models import Project
from src.app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from src.app.schemas.item import ItemOut
from src.app.api.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["projects"],
)

@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Create a new project.
    """
    existing = db.query(Project).filter(
        Project.project_number == project.project_number
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project number {project.project_number} already exists.",
        )

    db_project = Project(
        project_name=project.project_name,
        project_number=project.project_number,
        state=project.state,
        year=project.year,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/", response_model=List[ProjectOut])
def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    state: Optional[str] = Query(None, max_length=2),
    year: Optional[int] = Query(None, ge=1900),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Retrieve a list of projects, optionally filtered by state and/or year.
    """
    query = db.query(Project)

    if state:
        query = query.filter(Project.state == state)
    if year:
        query = query.filter(Project.year == year)

    return query.offset(skip).limit(limit).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Retrieve a specific project by ID.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    project: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Update an existing project.
    """
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    for key, value in project.dict(exclude_unset=True).items():
        setattr(db_project, key, value)

    db.commit()
    db.refresh(db_project)
    return db_project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Delete a project and all its associated items.
    """
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    db.delete(db_project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/items", response_model=List[ItemOut])
def get_project_items(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Retrieve all items associated with a specific project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    return project.items
