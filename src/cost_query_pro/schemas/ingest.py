"""src/cost_query_pro/schemas/ingest.py"""

from typing import Literal, Optional

from pydantic import BaseModel


class IngestRowResult(BaseModel):
    row: int
    status: Literal["inserted", "skipped", "failed"]
    reason: Optional[str] = None


class IngestReport(BaseModel):
    upload_id: int
    filename: str
    records_inserted: int
    records_skipped: int
    records_failed: int
    issues: list[IngestRowResult]
