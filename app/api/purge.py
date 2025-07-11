from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.api.auth import get_current_admin
from app.db.session import get_db
from app.models import Project, Item

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"]
)

@router.delete("/purge")
def purge_data(
    year_cutoff: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """
    Delete all projects and related items older than the specified year_cutoff.
    Admin-only route.
    """
    old_projects = db.query(Project).filter(Project.year < year_cutoff).all()

    if not old_projects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No projects older than {year_cutoff} found."
        )

    deleted_projects_count = 0
    deleted_items_count = 0

    for project in old_projects:
        items_deleted = db.query(Item).filter(Item.project_id == project.id).delete()
        deleted_items_count += items_deleted

        db.delete(project)
        deleted_projects_count += 1

    db.commit()

    logger.info(
        f"Purged {deleted_projects_count} projects and {deleted_items_count} items older than {year_cutoff}."
    )

    return {
        "message": f"Data older than {year_cutoff} has been purged.",
        "projects_deleted": deleted_projects_count,
        "items_deleted": deleted_items_count,
    }
