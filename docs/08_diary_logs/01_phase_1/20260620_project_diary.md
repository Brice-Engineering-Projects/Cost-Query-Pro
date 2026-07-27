---
title: Phase 1 — Core API Cleanup, Pyright Zero-Error, and Ingestion Pipeline
date: 2026-06-20
module: Core API · Type Safety · Ingestion Pipeline
type: project
tags: fastapi, sqlalchemy, pydantic, alembic, pyright, ingestion, csv, excel
author: Brice Nelson
author_link: https://github.com/Brice-Engineering-Projects/Cost-Query-Pro
status: Completed
---

========================================================

Date: 2026-06-20 — Full session

========================================================

## Cost Query Pro — Phase 1 Session Summary

This session completed three major work streams:

1. **Core API polish** — duplicate route removal, deterministic sort order, structured error codes
2. **Pyright zero-error** — resolved 84 type errors across all active source files
3. **Ingestion Pipeline** — full CSV/Excel upload endpoint with validation, idempotency, lineage, and tests

At the start of the session, 66 tests were passing. At the end: **72 tests passing, 0 pyright errors**.

---

## Part 1 — Core API Cleanup

### Tasks Completed

- **Removed duplicate `GET /items/search` route.** A dead placeholder route existed below the real search implementation and was silently shadowed. Removed entirely.
- **Added deterministic sort order** to all paginated queries. Without `.order_by()`, SQLAlchemy returns rows in an undefined order that can differ between runs, breaking pagination and making tests fragile.
  - `GET /api/v1/projects` → `.order_by(Project.id)`
  - `GET /api/v1/items/search` → `.order_by(Item.id)`
  - `GET /api/v1/items/units` (distinct) → `.order_by(Item.unit)`
  - `GET /api/v1/projects/{id}/items` — switched from `project.items` relationship to an explicit query with `.order_by(Item.id)` to allow ordering
- **Structured error codes (Option B — `AppError`).** Replaced all raw `HTTPException` raises across the codebase with a custom `AppError(code, message, status_code)` exception. Three global handlers registered on `app`:
  - `AppError` → `{"code": "...", "message": "..."}`
  - `HTTPException` fallback → `{"code": "HTTP_ERROR", "message": "..."}`
  - `RequestValidationError` → `{"code": "VALIDATION_ERROR", "message": "...", "errors": [...]}`
  - Error codes defined per domain: `ITEM_NOT_FOUND`, `PROJECT_NOT_FOUND`, `PROJECT_NUMBER_CONFLICT`, `INVALID_CREDENTIALS`, `USERNAME_TAKEN`, `PASSWORD_TOO_SHORT`, `USER_NOT_FOUND`, `SELF_DELETE_FORBIDDEN`, `USER_ALREADY_ADMIN`, `NO_PROJECTS_FOUND`, `ADMIN_REQUIRED`, `UNAUTHORIZED`
  - All test assertions updated from `detail` key checks to `code` key checks.

### Design Decision: Option B over Options A and C

**Option A** (dict in `HTTPException.detail`) keeps using `HTTPException` but stuffs a dict into `detail`. Works but is non-standard and forces every caller to check `response.json()["detail"]["code"]` — awkward.

**Option B** (custom exception class) is clean, type-safe, and gives global handlers full control over response shape. Every raise site reads naturally: `raise AppError("ITEM_NOT_FOUND", "Item not found.", 404)`.

**Option C** (RFC 7807 Problem Details) is the HTTP standard but adds schema complexity and is overkill for an internal API at this stage.

Option B was chosen as the right balance of clarity and simplicity.

---

## Part 2 — Pyright Zero-Error (84 → 0)

### Root Causes and Fixes

This was the most technically involved part of the session. Pyright surfaced 84 errors across 6+ files. The root causes fell into four categories:

#### 1. pydantic-settings v2 API change
`Field(default, env="NAME")` is no longer valid in pydantic-settings v2. The library now auto-maps field names to environment variables — no `env=` kwarg needed.

- **Fix:** Removed all `env=` arguments from every `Field()` call in `config/settings.py`.
- Also replaced `ConfigDict` (pydantic) with `SettingsConfigDict` (pydantic_settings) for the `model_config`.
- `alias="ALLOW_ADMIN_SIGNUP"` was also removed since auto-mapping handles it.

#### 2. SQLAlchemy 1.x `Column(T)` vs 2.0 `Mapped[T]`
Old-style `id = Column(Integer, ...)` gives pyright `Column[int]` — an unresolvable opaque type that breaks every conditional (`if user.is_admin:`) and every type-checked call. The fix is to migrate to `Mapped[T] = mapped_column(...)` which lets pyright see the plain Python type.

- **Models migrated this session:** `User`, `Item`, `SystemSetting`, `UploadHistory`, `DataQualityIssue`, `Project`
- `User.is_admin: Mapped[bool]` resolved a `ColumnElement[bool]` conditional error in `admin_users.py`
- `Item.unit_price: Mapped[float]` resolved a type mismatch when constructing `Decimal(str(item.unit_price))`
- `SystemSetting.__eq__` returning `ColumnElement[bool]` instead of `bool` was fixed with `Mapped[T]` + explicit `-> bool` annotation

#### 3. Deprecated pydantic v2 `example=` field
pydantic v2 replaced `Field(..., example=...)` with `Field(..., examples=[...])` (a list). Updated throughout `schemas/item.py` and `schemas/project.py`.

#### 4. Miscellaneous annotation gaps
- `security.py`: `username: str | None = payload.get("sub")` — `.get()` returns `Any | None`, not `str`
- `deps/payloads.py`: `UserCreate(**data)` → `UserCreate.model_validate(data)` — splat of form-parsed dict caused a pyright type mismatch
- `schemas/item.py`: `ItemWithProject` computed properties had unreachable `else None` branches typed as `-> str`. Removed the dead branches.

### Challenge: 4 Remaining Errors After Initial Pass

After the first fix pass, 4 errors remained:

1. `security.py:76` — `str` assignment from `.get()` (fixed: `str | None`)
2. `settings.py:50` — remaining `env=` kwarg in one field (fixed)
3. `settings.py:55` — `SettingsConfigDict` not imported (fixed)
4. `settings.py:64` — `# type: ignore[call-arg]` needed on `Settings()` instantiation (added)

These were caught on a second pyright run and resolved individually.

---

## Part 3 — Ingestion Pipeline

### Design Decisions Made

Before implementation, four design questions were posed and answered:

| Question | Decision | Reasoning |
|----------|----------|-----------|
| **Q1: Header matching** | Case-insensitive (strip + lowercase) | Source files from different agencies have inconsistent casing. Hard requirements on exact header names would cause unnecessary failures. |
| **Q2: Idempotency key** | `(project_number, item_description, unit)` | Minimal natural key that uniquely identifies a bid item within a project. Adding `unit_price` would cause re-uploads with updated prices to create duplicates instead of being skipped. |
| **Q3: PDF support** | Deferred to Phase 2 | PDF extraction (pdfplumber) adds complexity and edge cases that are out of scope for the Phase 1 MVP. CSV and Excel cover the immediate need. |
| **Q4: Upload lineage** | Per-row `upload_id` FK on `items` | Allows tracing every row back to its source upload, supporting future audit, deduplication analysis, and re-ingestion workflows. |

### Model Bugs Fixed

Two existing models had never been wired correctly:

**`UploadHistory`:**
- Used old `Column(...)` style → migrated to `Mapped[T]`
- `back_populates="uploads"` referenced a relationship that didn't exist on `User` — fixed by adding `uploads` to `User`
- Missing fields added: `file_type`, `records_skipped`, `records_failed`
- Added `items` back-reference for per-row lineage

**`DataQualityIssue`:**
- `ForeignKey("uploads.id")` — wrong table name (table is `upload_history`, not `uploads`) — fixed
- `relationship("Upload", ...)` — wrong class name (class is `UploadHistory`, not `Upload`) — fixed
- Added `row_number` column (needed to identify which row failed)
- Migrated to `Mapped[T]`

### Alembic Migration Fix

The `migrations/env.py` file only imported `Base` from `cost_query_pro.db` but did **not** import any model modules. This meant `Base.metadata` was empty — autogenerate would detect all existing tables as "removed" and generate a catastrophic DROP TABLE migration.

**Fix:** Added `import cost_query_pro.models` to `env.py`. This registers all models with the metadata before autogenerate runs.

The first autogenerate run (before the fix) produced a migration that would have dropped `users`, `projects`, `items`, and `audit_logs`. That file was deleted and regenerated after the fix.

### Ingestion Service Architecture

The pipeline in `services/ingestion.py` follows a single-pass approach:

```
parse → normalize headers → validate columns → per-row loop:
    validate values → get/create project → idempotency check → insert
→ write UploadHistory record → write DataQualityIssue records → return IngestReport
```

Key decisions:
- **Project auto-creation:** If a `project_number` is not found, the service attempts to create the project using optional columns (`project_name`, `state`, `year`). If `year` is missing or invalid, the row fails with `PROJECT_ERROR`.
- **Partial failure is not a pipeline failure:** A row that fails validation or project lookup is recorded in `DataQualityIssue` and counted in `records_failed`, but processing continues for remaining rows. The upload status is `"success"` if no failures, `"partial"` if any.
- **`UploadHistory` committed at the end:** The record is created with `status="pending"` and counts updated only after all rows are processed, then committed in one shot.

### Pyright Errors Found Post-Ingestion

After implementation, pyright found 3 errors:

1. **`ingestion.py:226`** — `project.id` typed as `Column[int]` because `Project` was still using old `Column(...)` style. Fixed by migrating `Project` to `Mapped[T]` (consistent with all other models now).

2. **`test_ingest.py:46,48`** — `wb.active` returns `Worksheet | None`; calling `.append()` on a possibly-`None` value. Fixed with `assert ws is not None` after `wb.active`.

3. **`migration:87`** — `op.drop_constraint(None, ...)` — autogenerate passed `None` as the constraint name when the FK was created without an explicit name. Fixed by:
   - Querying the DB to find the actual PostgreSQL-assigned constraint name: `items_upload_id_fkey`
   - Updating both `create_foreign_key` (upgrade) and `drop_constraint` (downgrade) to use the explicit name

---

## Lessons Learned

### Always import models in `alembic/env.py`
The `Base.metadata` is populated by importing model modules — SQLAlchemy registers each table when the class is defined. If `env.py` only imports `Base` without the models, autogenerate sees an empty metadata and interprets every existing table as "to be dropped." This is a silent footgun that produces a destructive migration. **Fix: add `import cost_query_pro.models` to `env.py` and keep it there.**

### Migrate SQLAlchemy models to `Mapped[T]` incrementally as you touch them
Old-style `Column(Integer)` is untyped from pyright's perspective. As each model was touched for feature work, it was worth migrating to `Mapped[T] = mapped_column(...)` at the same time. This pays forward: all future code against those models gets proper type inference at zero additional cost.

### Name your Alembic FK constraints explicitly
Autogenerate passes `None` as the constraint name when none is specified, which PostgreSQL silently names `{table}_{column}_fkey`. The generated downgrade uses `None` for the drop, which fails pyright. Naming constraints explicitly (e.g., `"items_upload_id_fkey"`) makes migrations self-documenting and avoids pyright errors.

### pydantic-settings v2 auto-maps field names
The `env=` kwarg in `Field()` was valid in pydantic-settings v1. In v2, field names are automatically mapped to environment variable names (uppercase). Removing `env=` throughout `settings.py` resolved 50+ pyright errors in one change.

### Structured errors pay off in test readability
Switching from `HTTPException` with string `detail` to `AppError` with typed `code` fields made test assertions cleaner (`resp.json()["code"] == "ITEM_NOT_FOUND"`) and made error handling more consistent across the entire API surface.

---

## Phase 1 Status After This Session

| Section | Status |
|---------|--------|
| Authentication | Complete (JWT, bcrypt, register/login/me, admin guards, password policy) |
| Core API | Complete (CRUD for projects/items, search, structured errors, sort order) |
| Schema & Migrations | Complete (5 migrations, all models Mapped[T], upload_history + data_quality_issues fixed) |
| Ingestion Pipeline | Complete (CSV + Excel, validation, idempotency, lineage, 6 tests) |
| CI / Test Suite | 72 tests passing, 0 pyright errors |
| Deferred to Phase 2 | PDF ingestion, refresh tokens, login throttling, RBAC, OpenAPI verification |

---

## Next Up — Phase 2 Candidates

- **AI Agent Search** — natural language cost queries backed by Claude, returning cited project records
- **Refresh token flow** — Redis-backed token rotation with `/auth/refresh` and `/auth/logout`
- **Login throttling** — `slowapi` rate limiter on `/auth/login` to support locked-account scenarios
- **Ingestion reliability** — job state machine, downloadable error reports, retry logic
- **Admin workflows** — audit log retrieval endpoint, user lifecycle
- **RBAC** — `roles`, `permissions`, `role_permissions` tables replacing binary `is_admin` flag
- **Search performance** — indexing, query tuning, P95 latency target
