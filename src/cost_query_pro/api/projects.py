"""src/cost_query_pro/api/projects.py"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from cost_query_pro.api.auth import get_current_user
from cost_query_pro.core.errors import AppError
from cost_query_pro.db.session import get_db
from cost_query_pro.models import Item, Project
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.item import ItemOut
from cost_query_pro.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
) -> Project:
    """
    Create a new project.
    """
    existing = (
        db.query(Project)
        .filter(Project.project_number == project.project_number)
        .first()
    )

    if existing:
        raise AppError(
            "PROJECT_NUMBER_CONFLICT",
            f"Project number {project.project_number} already exists.",
            400,
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
    current_user: DBUser = Depends(get_current_user),
) -> List[Project]:
    """
    Retrieve a list of projects, optionally filtered by state and/or year.
    """
    query = db.query(Project)

    if state:
        query = query.filter(Project.state == state)
    if year:
        query = query.filter(Project.year == year)

    return query.order_by(Project.id).offset(skip).limit(limit).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
) -> Project:
    """
    Retrieve a specific project by ID.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise AppError(
            "PROJECT_NOT_FOUND", f"Project with ID {project_id} not found.", 404
        )
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    project: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
) -> Project:
    """
    Update an existing project.
    """
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise AppError(
            "PROJECT_NOT_FOUND", f"Project with ID {project_id} not found.", 404
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
    current_user: DBUser = Depends(get_current_user),
) -> Response:
    """
    Delete a project and all its associated items.
    """
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise AppError(
            "PROJECT_NOT_FOUND", f"Project with ID {project_id} not found.", 404
        )

    db.delete(db_project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/items", response_model=List[ItemOut])
def get_project_items(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
) -> List[Item]:
    """
    Retrieve all items associated with a specific project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise AppError(
            "PROJECT_NOT_FOUND", f"Project with ID {project_id} not found.", 404
        )

    return db.query(Item).filter(Item.project_id == project_id).order_by(Item.id).all()
