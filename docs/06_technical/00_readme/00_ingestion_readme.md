# Ingestion Guide

Upload historical bid item data into Cost Query Pro via a CSV or Excel file. PDF ingestion is a Phase 2 requirement and will extend the same validation and reporting flow to PDF bid tabulations. The endpoint validates, deduplicates, and stores rows, then returns a structured report showing what was inserted, skipped, or failed.

---

## Endpoint

```
POST /api/v1/ingest/upload
```

**Authentication:** JWT bearer token required (any authenticated user).

**Content-Type:** `multipart/form-data`

---

## Supported File Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | `.csv` | UTF-8 or UTF-8-BOM encoded |
| Excel | `.xlsx` | Active sheet only; first row must be headers |

PDF is deferred to Phase 2. When implemented, it must parse bid tabulation tables and extract `project_number` from page-level footer/header metadata when the value is not present in table columns.

---

## Required Columns

Every file must contain these five columns. Column names are matched **case-insensitively** and leading/trailing whitespace is stripped, so `Unit Price`, `unit_price`, and `UNIT_PRICE` are all accepted.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `project_number` | string | non-empty | Unique identifier for the project (e.g. `P-2023-042`) |
| `item_description` | string | non-empty | Description of the bid line item |
| `unit` | string | non-empty | Unit of measure (e.g. `LF`, `EA`, `CY`) |
| `unit_price` | decimal | `>= 0` | Cost per unit |
| `quantity` | integer | `>= 0` | Quantity of units |

If any required column is missing from the file header, the entire upload is rejected before any rows are processed (`INGEST_MISSING_COLUMNS`).

---

## Optional Columns

These columns are used to create or enrich project records. They are not required but improve data quality.

| Column | Type | Default if absent | Description |
|--------|------|-------------------|-------------|
| `project_name` | string | `project_number` | Human-readable project name |
| `state` | string (2-char) | `XX` | Two-letter US state code (e.g. `TX`, `CA`) |
| `year` | integer | — | Bid year (1900–2100). **Required to create a new project.** If omitted or invalid and the project does not already exist, the row fails. |

---

## Template

Minimum viable CSV (copy and fill in your data):

```csv
project_number,project_name,state,year,item_description,unit,unit_price,quantity
P-2024-001,Main St Waterline,TX,2024,8" DIP Water Main,LF,85.50,1200
P-2024-001,Main St Waterline,TX,2024,Fire Hydrant Assembly,EA,4200.00,3
```

---

## How to Upload

### curl

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -F "file=@/path/to/your/file.csv"
```

### Python (requests)

```python
import requests

token = "<your_jwt_token>"
with open("bid_items.csv", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/ingest/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bid_items.csv", f, "text/csv")},
    )
print(response.json())
```

---

## Response

A successful upload returns HTTP `201` with an `IngestReport`:

```json
{
  "upload_id": 42,
  "filename": "bid_items.csv",
  "records_inserted": 18,
  "records_skipped": 2,
  "records_failed": 1,
  "issues": [
    {
      "row": 5,
      "status": "skipped",
      "reason": null
    },
    {
      "row": 11,
      "status": "failed",
      "reason": "unit_price must be >= 0"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `upload_id` | ID of the `UploadHistory` record for this run |
| `filename` | Original filename as uploaded |
| `records_inserted` | Rows successfully written to the database |
| `records_skipped` | Rows that already existed (duplicate key) |
| `records_failed` | Rows that failed validation or project lookup |
| `issues` | Per-row detail for every skipped or failed row |

The `issues` array contains only skipped and failed rows. Inserted rows are not included.

---

## Deduplication

Rows are deduplicated by the composite key **`(project_number, item_description, unit)`**. If a matching item already exists in the database, the row is counted as `skipped` and no update is made. Re-uploading the same file is safe.

---

## Row-Level Validation

Each row is validated independently. A failure on one row does not affect others.

| Check | Error |
|-------|-------|
| `unit_price` is not a number | `failed` — conversion error |
| `unit_price < 0` | `failed` — `unit_price must be >= 0` |
| `quantity` is not an integer | `failed` — conversion error |
| `quantity < 0` | `failed` — `quantity must be >= 0` |
| `project_number`, `item_description`, or `unit` is blank | `failed` — `Empty required string field` |
| Project does not exist and `year` is missing or invalid | `failed` — `Cannot create project '...': missing or invalid 'year' column` |

---

## Project Auto-Creation

If `project_number` is not already in the database, the service creates a new `Project` record from the row's optional columns. The `year` column must be present and valid (1900–2100) for this to succeed. If `year` is missing or out of range, all rows belonging to that new project number will fail.

If the project already exists, `project_name`, `state`, and `year` from the file are ignored — the existing record is used as-is.

---

## Upload Status

The `UploadHistory` record is set to:

| Status | Condition |
|--------|-----------|
| `success` | Zero failed rows |
| `partial` | One or more failed rows |

Skipped rows do not affect the upload status.

---

## Error Codes

These errors are returned for the entire upload before row processing begins:

| Code | HTTP | Cause |
|------|------|-------|
| `INGEST_UNSUPPORTED_FORMAT` | 422 | File is not `.csv` or `.xlsx` |
| `INGEST_EMPTY_FILE` | 422 | File has no content or no data rows |
| `INGEST_MISSING_COLUMNS` | 422 | One or more required columns absent from header |
| `UNAUTHORIZED` | 401 | No or invalid JWT token |
