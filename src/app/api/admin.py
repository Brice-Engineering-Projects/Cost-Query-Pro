"""src/app/api/admin.py"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from src.app.core.security import get_current_admin
from src.app.db import get_db
from src.app.models import Project, Item
from src.app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"]
)

@router.delete("/purge")
def purge_data(
    year_cutoff: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Delete all projects and items older than the specified year_cutoff.

    Requires admin authentication.
    """
    old_projects = db.query(Project).filter(Project.year < year_cutoff).all()

    if not old_projects:
        raise HTTPException(
            status_code=404,
            detail=f"No projects older than {year_cutoff} found."
        )

    deleted_projects = 0
    deleted_items = 0

    for project in old_projects:
        items_deleted = db.query(Item).filter(Item.project_id == project.id).delete()
        deleted_items += items_deleted
        db.delete(project)
        deleted_projects += 1

    db.commit()

    logger.info(
        f"Purged {deleted_projects} projects and {deleted_items} items older than {year_cutoff}."
    )

    return {
        "message": f"Data older than {year_cutoff} has been purged.",
        "projects_deleted": deleted_projects,
        "items_deleted": deleted_items,
    }
