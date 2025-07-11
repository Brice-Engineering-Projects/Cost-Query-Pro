"""app/api/projects.py"""
"""app/api/projects.py"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.project import Project
from app.models.item import Item
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter()

@router.get("/", response_model=List[ProjectOut])
def get_projects(
    skip: int = 0,
    limit: int = 100,
    state: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of projects with optional filtering by state and year.
    """
    query = db.query(Project)

    if state:
        query = query.filter(Project.state == state)
    if year:
        query = query.filter(Project.year == year)

    return query.offset(skip).limit(limit).all()

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific project by ID.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return project

@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.
    """
    # Check if project number already exists
    existing = db.query(Project).filter(Project.project_number == project.project_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with number {project.project_number} already exists"
        )

    db_project = Project(
        project_name=project.project_name,
        project_number=project.project_number,
        state=project.state,
        year=project.year
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db)):
    """
    Update an existing project.
    """
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    # Update project attributes
    for key, value in project.dict(exclude_unset=True).items():
        setattr(db_project, key, value)

    db.commit()
    db.refresh(db_project)
    return db_project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project and all its associated items.
    """
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    db.delete(db_project)
    db.commit()
    return None

@router.get("/{project_id}/items", response_model=List)
def get_project_items(project_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all items associated with a specific project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    return project.items

@router.get("/by-year/{year}", response_model=List[ProjectOut])
def get_projects_by_year(year: int, db: Session = Depends(get_db)):
    """
    Retrieve all projects from a specific year.
    """
    projects = db.query(Project).filter(Project.year == year).all()
    return projects

@router.get("/by-state/{state}", response_model=List[ProjectOut])
def get_projects_by_state(state: str, db: Session = Depends(get_db)):
    """
    Retrieve all projects from a specific state.
    """
    projects = db.query(Project).filter(Project.state == state).all()
    return projects
