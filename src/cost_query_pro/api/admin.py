"""src/cost_query_pro/api/admin.py"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging
from typing import Dict, Any

from cost_query_pro.core.security import get_current_admin
from cost_query_pro.db import get_db
from cost_query_pro.models import Project, Item
from cost_query_pro.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


@router.delete("/purge")
def purge_data(
        year_cutoff: int = Query(..., description="Purge data older than this year"),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Delete all projects and items older than the specified year_cutoff.
    Requires admin authentication.
    """
    # Find projects older than the cutoff year
    old_projects = db.query(Project).filter(Project.year < year_cutoff).all()

    if not old_projects:
        return {
            "message": f"No projects older than {year_cutoff} found.",
            "projects_deleted": 0,
            "items_deleted": 0
        }

    # Perform the purge operation
    purge_results = _purge_old_projects(db, old_projects)

    # Log the results
    logger.info(
        f"Purged {purge_results['projects_deleted']} projects and "
        f"{purge_results['items_deleted']} items older than {year_cutoff}."
    )

    return {
        "message": f"Data older than {year_cutoff} has been purged.",
        "projects_deleted": purge_results["projects_deleted"],
        "items_deleted": purge_results["items_deleted"],
    }


def _purge_old_projects(db: Session, projects: list[Project]) -> Dict[str, int]:
    """
    Delete the specified projects and their related items.
    
    Args:
        db: Database session
        projects: List of projects to delete
        
    Returns:
        Dictionary with counts of deleted projects and items
    """
    projects_deleted = 0
    items_deleted = 0

    for project in projects:
        # Delete associated items first
        items_count = db.query(Item).filter(Item.project_id == project.id).delete()
        items_deleted += items_count

        # Delete the project
        db.delete(project)
        projects_deleted += 1

    # Commit all changes at once
    db.commit()

    return {
        "projects_deleted": projects_deleted,
        "items_deleted": items_deleted,
    }
