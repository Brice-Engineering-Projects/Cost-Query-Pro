"""src/cost_query_pro/api/purge.py"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session, joinedload

from cost_query_pro.core.errors import AppError
from cost_query_pro.core.security import get_current_admin
from cost_query_pro.db.session import get_db
from cost_query_pro.models.archived_item import ArchivedItem
from cost_query_pro.models.archived_project import ArchivedProject
from cost_query_pro.models.project import Project
from cost_query_pro.models.user import User as DBUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.delete("/purge", status_code=status.HTTP_200_OK)
def purge_data(
    year_cutoff: int = Query(..., description="Delete projects older than this year"),
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
) -> dict[str, Any]:
    """
    Delete all projects and related items older than the specified year_cutoff.
    Accessible by admin users only.
    """
    old_projects = (
        db.query(Project)
        .options(joinedload(Project.items))
        .filter(Project.year < year_cutoff)
        .all()
    )

    if not old_projects:
        raise AppError(
            "NO_PROJECTS_FOUND",
            f"No projects older than {year_cutoff} found.",
            404,
        )

    deleted_projects_count = len(old_projects)
    deleted_items_count = sum(len(project.items) for project in old_projects)

    try:
        for project in old_projects:
            archived_project = ArchivedProject(
                id=project.id,
                project_name=project.project_name,
                project_number=project.project_number,
                state=project.state,
                year=project.year,
                purged_by_user_id=current_admin.id,
            )
            db.add(archived_project)

            for item in project.items:
                db.add(
                    ArchivedItem(
                        id=item.id,
                        project_id=project.id,
                        item_description=item.item_description,
                        unit=item.unit,
                        unit_price=item.unit_price,
                        quantity=item.quantity,
                        upload_id=item.upload_id,
                    )
                )

            db.delete(project)

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to purge and archive data", exc_info=exc)
        raise AppError(
            "PURGE_ARCHIVE_FAILED",
            "Failed to archive records during purge; no data was deleted.",
            500,
        )

    logger.info(
        f"Admin '{current_admin.username}' purged {deleted_projects_count} projects "
        f"and {deleted_items_count} items older than {year_cutoff}."
    )

    return {
        "message": f"Data older than {year_cutoff} has been purged.",
        "projects_deleted": deleted_projects_count,
        "items_deleted": deleted_items_count,
    }
