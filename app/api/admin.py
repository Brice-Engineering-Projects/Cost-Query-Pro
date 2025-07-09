"""app/api/admin.py"""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_admin
from app.db import get_db
from app.models import Project, Item


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.delete("/purge")
def purge_data(
    year_cutoff: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Delete old projects + items older than year_cutoff."""
    old_projects = db.query(Project).filter(Project.year < year_cutoff).all()

    if not old_projects:
        return {"message": f"No projects older than {year_cutoff} found."}

    deleted_projects = 0
    deleted_items = 0

    for project in old_projects:
        items_deleted = db.query(Item).filter(Item.project_id == project.id).delete()
        deleted_items += items_deleted
        db.delete(project)
        deleted_projects += 1

    db.commit()

    return {
        "message": f"Data older than {year_cutoff} has been purged.",
        "projects_deleted": deleted_projects,
        "items_deleted": deleted_items,
    }
