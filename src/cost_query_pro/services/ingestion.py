"""
src/cost_query_pro/services/ingestion.py

Ingestion service for processing CSV and Excel bid item uploads.
"""

import csv
import io
from typing import Any

import openpyxl
from sqlalchemy.orm import Session

from cost_query_pro.core.errors import AppError
from cost_query_pro.models.data_quality_issue import DataQualityIssue
from cost_query_pro.models.item import Item
from cost_query_pro.models.project import Project
from cost_query_pro.models.upload_history import UploadHistory
from cost_query_pro.schemas.ingest import IngestReport, IngestRowResult

REQUIRED_COLUMNS = {
    "project_number",
    "item_description",
    "unit",
    "unit_price",
    "quantity",
}


def _normalize_headers(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with all keys stripped and lowercased."""
    return {k.strip().lower(): v for k, v in raw.items()}


def _parse_csv(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _parse_excel(content: bytes) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
    result = []
    for row in rows[1:]:
        result.append(
            {
                headers[i]: (row[i] if i < len(row) else None)
                for i in range(len(headers))
            }
        )
    wb.close()
    return result


def _get_or_create_project(db: Session, row: dict[str, Any]) -> Project | None:
    """Look up project by project_number; create if missing and enough data is present."""
    project_number = str(row["project_number"]).strip()
    project = db.query(Project).filter(Project.project_number == project_number).first()
    if project:
        return project

    project_name = (
        str(row.get("project_name", project_number)).strip() or project_number
    )
    state_raw = str(row.get("state", "")).strip().upper()
    state = state_raw if len(state_raw) == 2 else "XX"
    try:
        year = int(row.get("year", 0))
        if year < 1900 or year > 2100:
            year = 0
    except (ValueError, TypeError):
        year = 0

    if year == 0:
        return None

    project = Project(
        project_number=project_number,
        project_name=project_name,
        state=state,
        year=year,
    )
    db.add(project)
    db.flush()
    return project


def _item_exists(
    db: Session, project_id: int, item_description: str, unit: str
) -> bool:
    return (
        db.query(Item)
        .filter(
            Item.project_id == project_id,
            Item.item_description == item_description,
            Item.unit == unit,
        )
        .first()
        is not None
    )


def run_ingestion(
    db: Session,
    content: bytes,
    filename: str,
    file_type: str,
    user_id: int,
) -> IngestReport:
    """
    Parse, validate, deduplicate, and store bid items from an uploaded file.

    Args:
        db: SQLAlchemy session
        content: raw file bytes
        filename: original filename (for audit record)
        file_type: "csv" or "xlsx"
        user_id: ID of the authenticated user performing the upload

    Returns:
        IngestReport with counts and per-row results for failed rows
    """
    # 1. Parse raw rows
    if file_type == "csv":
        raw_rows = _parse_csv(content)
    elif file_type == "xlsx":
        raw_rows = _parse_excel(content)
    else:
        raise AppError(
            "INGEST_UNSUPPORTED_FORMAT", f"Unsupported file type: {file_type}", 422
        )

    if not raw_rows:
        raise AppError(
            "INGEST_EMPTY_FILE", "The uploaded file contains no data rows.", 422
        )

    # 2. Normalize headers (already done for Excel; CSV needs it)
    rows = [_normalize_headers(r) for r in raw_rows]

    # 3. Validate required columns present in the first row
    first_keys = set(rows[0].keys())
    missing = REQUIRED_COLUMNS - first_keys
    if missing:
        raise AppError(
            "INGEST_MISSING_COLUMNS",
            f"Missing required columns: {', '.join(sorted(missing))}",
            422,
        )

    # 4. Create UploadHistory record (counts filled in later)
    upload = UploadHistory(
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        records_inserted=0,
        records_skipped=0,
        records_failed=0,
        status="pending",
    )
    db.add(upload)
    db.flush()  # get upload.id

    row_results: list[IngestRowResult] = []
    inserted = 0
    skipped = 0
    failed = 0

    for row_idx, row in enumerate(rows, start=2):  # row 1 = header
        # 5. Validate required field values
        try:
            project_number = str(row["project_number"]).strip()
            item_description = str(row["item_description"]).strip()
            unit = str(row["unit"]).strip()
            unit_price = float(row["unit_price"])
            quantity = int(row["quantity"])

            if not project_number or not item_description or not unit:
                raise ValueError("Empty required string field")
            if unit_price < 0:
                raise ValueError("unit_price must be >= 0")
            if quantity < 0:
                raise ValueError("quantity must be >= 0")
        except (ValueError, TypeError, KeyError) as exc:
            reason = str(exc)
            row_results.append(
                IngestRowResult(row=row_idx, status="failed", reason=reason)
            )
            db.add(
                DataQualityIssue(
                    upload_id=upload.id,
                    row_number=row_idx,
                    issue_type="VALIDATION_ERROR",
                    description=reason,
                )
            )
            failed += 1
            continue

        # 6. Look up / create project
        project = _get_or_create_project(db, row)
        if project is None:
            reason = f"Cannot create project '{project_number}': missing or invalid 'year' column"
            row_results.append(
                IngestRowResult(row=row_idx, status="failed", reason=reason)
            )
            db.add(
                DataQualityIssue(
                    upload_id=upload.id,
                    row_number=row_idx,
                    issue_type="PROJECT_ERROR",
                    description=reason,
                )
            )
            failed += 1
            continue

        # 7. Idempotency check
        if _item_exists(db, project.id, item_description, unit):
            row_results.append(IngestRowResult(row=row_idx, status="skipped"))
            skipped += 1
            continue

        # 8. Insert row
        item = Item(
            project_id=project.id,
            item_description=item_description,
            unit=unit,
            unit_price=unit_price,
            quantity=quantity,
            upload_id=upload.id,
        )
        db.add(item)
        row_results.append(IngestRowResult(row=row_idx, status="inserted"))
        inserted += 1

    # 9. Update upload record with final counts
    upload.records_inserted = inserted
    upload.records_skipped = skipped
    upload.records_failed = failed
    upload.status = "success" if failed == 0 else "partial"
    db.commit()

    return IngestReport(
        upload_id=upload.id,
        filename=filename,
        records_inserted=inserted,
        records_skipped=skipped,
        records_failed=failed,
        issues=[r for r in row_results if r.status != "inserted"],
    )
