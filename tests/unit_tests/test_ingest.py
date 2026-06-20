"""tests/unit_tests/test_ingest.py"""

import io

import openpyxl

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_login(client, username="ingest_user", password="testpass123"):
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password, "is_admin": False},
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _csv_bytes(rows: list[dict]) -> bytes:
    """Build minimal CSV bytes from a list of row dicts (using the first dict's keys as headers)."""
    if not rows:
        return b""
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row[h]) for h in headers))
    return "\n".join(lines).encode()


def _xlsx_bytes(rows: list[dict]) -> bytes:
    """Build minimal XLSX bytes from a list of row dicts."""
    wb = openpyxl.Workbook()
    ws = wb.active
    if not rows:
        wb_bytes = io.BytesIO()
        wb.save(wb_bytes)
        return wb_bytes.getvalue()
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row[h] for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


SAMPLE_ROWS = [
    {
        "project_number": "TEST001",
        "project_name": "Test Project",
        "state": "FL",
        "year": 2023,
        "item_description": '8" PVC Gravity Sewer',
        "unit": "LF",
        "unit_price": 45.32,
        "quantity": 100,
    },
    {
        "project_number": "TEST001",
        "project_name": "Test Project",
        "state": "FL",
        "year": 2023,
        "item_description": "Manhole",
        "unit": "EA",
        "unit_price": 3500.00,
        "quantity": 2,
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_upload_csv_success(client):
    """Valid CSV file: all rows inserted, report reflects counts."""
    headers = _register_and_login(client, "csv_user")
    csv_data = _csv_bytes(SAMPLE_ROWS)

    resp = client.post(
        "/api/v1/ingest/upload",
        headers=headers,
        files={"file": ("items.csv", io.BytesIO(csv_data), "text/csv")},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["records_inserted"] == 2
    assert body["records_skipped"] == 0
    assert body["records_failed"] == 0
    assert body["filename"] == "items.csv"
    assert "upload_id" in body


def test_upload_excel_success(client):
    """Valid Excel file: all rows inserted."""
    headers = _register_and_login(client, "xlsx_user")
    xlsx_data = _xlsx_bytes(SAMPLE_ROWS)

    resp = client.post(
        "/api/v1/ingest/upload",
        headers=headers,
        files={
            "file": (
                "items.xlsx",
                io.BytesIO(xlsx_data),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["records_inserted"] == 2
    assert body["records_skipped"] == 0
    assert body["records_failed"] == 0


def test_upload_csv_idempotency(client):
    """Re-uploading the same CSV skips already-inserted rows."""
    headers = _register_and_login(client, "idem_user")
    csv_data = _csv_bytes(SAMPLE_ROWS)

    # First upload
    r1 = client.post(
        "/api/v1/ingest/upload",
        headers=headers,
        files={"file": ("items.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["records_inserted"] == 2

    # Second upload — same file, same rows
    r2 = client.post(
        "/api/v1/ingest/upload",
        headers=headers,
        files={"file": ("items.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert r2.status_code == 201, r2.text
    body = r2.json()
    assert body["records_inserted"] == 0
    assert body["records_skipped"] == 2
    assert body["records_failed"] == 0


def test_upload_csv_missing_columns(client):
    """CSV missing required columns returns 422 with INGEST_MISSING_COLUMNS code."""
    headers = _register_and_login(client, "missing_col_user")
    # Intentionally omit 'unit_price' and 'quantity'
    bad_rows = [
        {"project_number": "BAD001", "item_description": "Widget", "unit": "EA"},
    ]
    csv_data = _csv_bytes(bad_rows)

    resp = client.post(
        "/api/v1/ingest/upload",
        headers=headers,
        files={"file": ("bad.csv", io.BytesIO(csv_data), "text/csv")},
    )

    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "INGEST_MISSING_COLUMNS"


def test_upload_csv_partial_failure(client):
    """Rows with invalid values are recorded as failed; valid rows are still inserted."""
    headers = _register_and_login(client, "partial_user")
    mixed_rows = [
        # Valid row
        {
            "project_number": "PART001",
            "project_name": "Partial Project",
            "state": "GA",
            "year": 2022,
            "item_description": "Valid Item",
            "unit": "LF",
            "unit_price": 10.00,
            "quantity": 50,
        },
        # Invalid: negative unit_price
        {
            "project_number": "PART001",
            "project_name": "Partial Project",
            "state": "GA",
            "year": 2022,
            "item_description": "Bad Item",
            "unit": "EA",
            "unit_price": -5.00,
            "quantity": 1,
        },
    ]
    csv_data = _csv_bytes(mixed_rows)

    resp = client.post(
        "/api/v1/ingest/upload",
        headers=headers,
        files={"file": ("mixed.csv", io.BytesIO(csv_data), "text/csv")},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["records_inserted"] == 1
    assert body["records_failed"] == 1
    assert len(body["issues"]) == 1
    assert body["issues"][0]["status"] == "failed"


def test_upload_requires_auth(client):
    """Unauthenticated upload returns 401."""
    csv_data = _csv_bytes(SAMPLE_ROWS)

    resp = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("items.csv", io.BytesIO(csv_data), "text/csv")},
    )

    assert resp.status_code == 401, resp.text
