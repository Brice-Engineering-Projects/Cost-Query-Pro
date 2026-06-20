"""src/cost_query_pro/api/ingest.py"""

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from cost_query_pro.core.errors import AppError
from cost_query_pro.core.security import get_current_user
from cost_query_pro.db.session import get_db
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.ingest import IngestReport
from cost_query_pro.services.ingestion import run_ingestion

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _detect_file_type(filename: str, content_type: str) -> str:
    """Return 'csv' or 'xlsx' based on filename extension and content type."""
    name_lower = filename.lower()
    if name_lower.endswith(".csv"):
        return "csv"
    if name_lower.endswith(".xlsx"):
        return "xlsx"
    if "spreadsheetml" in content_type:
        return "xlsx"
    if "csv" in content_type or "text" in content_type:
        return "csv"
    raise AppError(
        "INGEST_UNSUPPORTED_FORMAT",
        "File must be a .csv or .xlsx file.",
        422,
    )


@router.post("/upload", response_model=IngestReport, status_code=201)
async def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
) -> IngestReport:
    """
    Upload a CSV or Excel file containing bid items.

    Rows are validated, deduplicated by (project_number, item_description, unit),
    and linked to the authenticated user via an UploadHistory record.
    """
    filename = file.filename or "upload"
    content_type = file.content_type or ""

    file_type = _detect_file_type(filename, content_type)
    content = await file.read()

    if not content:
        raise AppError("INGEST_EMPTY_FILE", "Uploaded file is empty.", 422)

    return run_ingestion(
        db=db,
        content=content,
        filename=filename,
        file_type=file_type,
        user_id=current_user.id,
    )
