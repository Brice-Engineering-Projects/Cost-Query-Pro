"""src/cost_query_pro/api/purge.py"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cost_query_pro.core.security import get_current_admin
from cost_query_pro.db.session import get_db
from cost_query_pro.models.item import Item
from cost_query_pro.models.project import Project
from cost_query_pro.models.user import User as DBUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.delete("/purge", status_code=status.HTTP_200_OK)
def purge_data(
    year_cutoff: int = Query(..., description="Delete projects older than this year"),
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Delete all projects and related items older than the specified year_cutoff.
    Accessible by admin users only.
    """
    old_projects = db.query(Project).filter(Project.year < year_cutoff).all()

    if not old_projects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No projects older than {year_cutoff} found.",
        )

    deleted_projects_count = len(old_projects)
    deleted_items_count = 0

    for project in old_projects:
        items_deleted = db.query(Item).filter(Item.project_id == project.id).delete()
        deleted_items_count += items_deleted
        db.delete(project)

    db.commit()

    logger.info(
        f"Admin '{current_admin.username}' purged {deleted_projects_count} projects "
        f"and {deleted_items_count} items older than {year_cutoff}."
    )

    return {
        "message": f"Data older than {year_cutoff} has been purged.",
        "projects_deleted": deleted_projects_count,
        "items_deleted": deleted_items_count,
    }
