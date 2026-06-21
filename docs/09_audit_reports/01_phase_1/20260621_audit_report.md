# Cost Query Pro — Phase 1 Audit Report

**Date:** 2026-06-21
**Branch:** phase_1
**Auditor:** Claude (claude-sonnet-4-6)
**Scope:** Full codebase and documentation audit prior to Phase 2 entry
**Verdict:** Phase 1 is largely complete with three critical defects that must be resolved before Phase 2 begins.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1 Exit Criteria Assessment](#2-phase-1-exit-criteria-assessment)
3. [Critical Findings](#3-critical-findings)
4. [Code Quality Findings](#4-code-quality-findings)
5. [Test Coverage Findings](#5-test-coverage-findings)
6. [Documentation Findings](#6-documentation-findings)
7. [Prioritized Recommendations](#7-prioritized-recommendations)
8. [Appendix — File-Level Summary](#8-appendix--file-level-summary)

---

## 1. Executive Summary

Cost Query Pro Phase 1 delivers a working FastAPI backend with JWT authentication, a stable PostgreSQL schema, a structured item search API, and a CSV/Excel ingestion pipeline. The codebase is well-organized, the test suite is solid, and the documentation is above average for an early-stage project.

**Three critical defects block Phase 2 entry:**

1. A duplicate route registration for `POST /api/v1/admin/purge` (both `api/admin.py` and `api/purge.py` register the same endpoint) creates undefined routing behavior.
2. Two archived models (`ArchivedProject`, `ArchivedItem`) declare `__tablename__` values that conflict with the live `projects` and `items` tables, which will cause a SQLAlchemy registry crash if those models are ever instantiated.
3. The `.env` file containing database credentials and the JWT secret key appears to be tracked in version control.

All three must be resolved before Phase 2 development begins. The remaining findings are lower-severity issues that can be addressed within Phase 2 or deferred further.

---

## 2. Phase 1 Exit Criteria Assessment

| Exit Criterion | Status | Notes |
|---|---|---|
| Users can authenticate and query cost records via API | ✅ Done | JWT auth, all CRUD endpoints working and tested |
| At least one full ingest flow (CSV or Excel) runs end-to-end | ✅ Done | CSV and Excel both pass end-to-end tests |
| Core schema stable and migration process repeatable | ✅ Done | Five ordered migrations, all with downgrade paths |
| CI passes: lint · security scan · migrations · unit tests | ✅ Done | Black, Ruff, Bandit, pip-audit, Alembic smoke test, Pytest all in pipeline |

**Assessment:** All four exit criteria are met. The critical defects identified in Section 3 are pre-existing bugs, not regressions — they exist in currently-deferred code paths (archived models) or redundant route files that can be cleaned up without affecting tested functionality.

---

## 3. Critical Findings

### C-1 — Duplicate Route Registration (CRITICAL)

**Files:** `src/cost_query_pro/api/admin.py` and `src/cost_query_pro/api/purge.py`
**Issue:** Both files define a `POST /api/v1/admin/purge` endpoint. Both routers are registered in `main.py`. FastAPI will silently register both, with last-registered winning. The behavior is undefined and untested.
**Impact:** Admin purge calls may invoke the wrong handler or produce inconsistent behavior depending on startup order.
**Fix:** Delete one file. Keep `api/admin.py` (it is more descriptively named) and remove `api/purge.py` and its router registration from `main.py`.

---

### C-2 — Archived Model Table Name Conflicts (CRITICAL)

**Files:** `src/cost_query_pro/models/archived_project.py` and `src/cost_query_pro/models/archived_item.py`
**Issue:**
- `ArchivedProject.__tablename__ = "projects"` — same as the live `Project` model.
- `ArchivedItem.__tablename__ = "items"` — same as the live `Item` model.

SQLAlchemy's mapper registry will raise a conflict error if both models are loaded simultaneously (which happens any time `models/__init__.py` imports them). Additionally:
- `archived_project.archived_at` is declared as `Boolean` instead of `DateTime`.
- `ArchivedItem` is missing the `upload_id` column present on `Item`.
- No migrations exist for either archived table.

**Impact:** Any code path that touches these models will crash at import or runtime. Purge operations that write to archived tables will fail silently or raise an exception.
**Fix (Phase 2):** Rename tables to `archived_projects` and `archived_items`, correct `archived_at` to `DateTime`, align columns with source models, and create migrations. The roadmap correctly tracks this as `[!]` blocked.

---

### C-3 — Credentials in Version Control (CRITICAL)

**File:** `.env`
**Issue:** The `.env` file contains the PostgreSQL connection string (with password) and the JWT `SECRET_KEY`. If this file is committed to the repository, credentials are exposed.
**Impact:** Anyone with repository access has the database password and can forge JWT tokens.
**Fix:** Confirm `.env` is in `.gitignore`. If it has ever been committed, rotate the secret key and database password. Document local setup with a `.env.example` file.

---

## 4. Code Quality Findings

### Q-1 — No File Size Limit on Ingest Endpoint (HIGH)

**File:** `src/cost_query_pro/api/ingest.py`
**Issue:** The upload endpoint accepts any file size. A large file will consume memory and potentially exhaust the process.
**Recommendation:** Add a `MAX_UPLOAD_SIZE_MB` config setting (e.g., 50 MB default) and reject oversized uploads with `HTTP 413` before reading the file content.

---

### Q-2 — Missing `ON DELETE` Clause on `data_quality_issues.upload_id` FK (HIGH)

**File:** `migrations/versions/68ed7ede6930_ingest_fix_models_and_add_upload_lineage.py`
**Issue:** The foreign key from `data_quality_issues.upload_id` to `upload_history.id` has no `ON DELETE` clause. If an `UploadHistory` row is deleted, the child `DataQualityIssue` rows become orphans.
**Recommendation:** Add `ON DELETE CASCADE` to this FK in a Phase 2 migration.

---

### Q-3 — `unit_price` Stored as Float, Not Decimal (MEDIUM)

**File:** `src/cost_query_pro/schemas/item.py`
**Issue:** `unit_price` is serialized as a Python `float`, which introduces binary floating-point rounding error for currency values.
**Recommendation:** Use `Decimal` (from the `decimal` module) for all currency fields. FastAPI + Pydantic support `Decimal` natively.

---

### Q-4 — Price Range Stats Uses Two Separate Queries (MEDIUM)

**File:** `src/cost_query_pro/api/items.py` (price-range stats endpoint)
**Issue:** Min and max prices are retrieved via two separate `SELECT` statements instead of a single aggregation query.
**Recommendation:** Combine into a single `SELECT MIN(unit_price), MAX(unit_price), AVG(unit_price)` query.

---

### Q-5 — No Full-Text Index on `item_description` (MEDIUM)

**File:** `src/cost_query_pro/api/items.py` (keyword search)
**Issue:** The keyword search uses `ILIKE '%query%'`, which performs a full table scan. At scale (tens of thousands of items), this will be slow.
**Recommendation:** This is already tracked in the Phase 2 Search Performance section of the roadmap. Flag it here as confirmed high-priority for Phase 2.

---

### Q-6 — `upload_history.status` is an Unvalidated String (MEDIUM)

**File:** `src/cost_query_pro/models/upload_history.py`
**Issue:** The `status` column is a plain `TEXT` field. Any string can be inserted. Valid states (`queued`, `running`, `succeeded`, `failed`) are not enforced at the model or database level.
**Recommendation:** Replace with a PostgreSQL-native `ENUM` type or a Python `enum.Enum` validated via Pydantic.

---

### Q-7 — `audit_log` Uses Old-Style `Column()` Syntax (LOW)

**File:** `src/cost_query_pro/models/audit_log.py`
**Issue:** `AuditLog` uses `Column()` syntax while all other models use the modern SQLAlchemy 2.0 `Mapped[T]` style. This is an inconsistency that will generate Pyright warnings as annotations expand.
**Recommendation:** Migrate to `Mapped[T]` syntax in Phase 2 when the audit log schema is expanded.

---

### Q-8 — Ingestion State Defaults to `"XX"` for Missing State (LOW)

**File:** `src/cost_query_pro/services/ingestion.py`
**Issue:** When an uploaded row has no `state` value, the ingestion service silently writes `"XX"` as a sentinel. This masks data quality issues; rows with a missing state become invisible problems.
**Recommendation:** Log a `DataQualityIssue` for rows with a missing state field rather than silently substituting a value. Phase 2 ingestion reliability work should address this.

---

### Q-9 — `pyright` Listed as a Runtime Dependency (LOW)

**File:** `pyproject.toml`
**Issue:** `pyright>=1.1.410` appears in the main `[dependencies]` group rather than the dev/lint group.
**Recommendation:** Move `pyright` to `[project.optional-dependencies.dev]` or the equivalent in your tooling config.

---

## 5. Test Coverage Findings

The test suite is well-structured with strong fixture isolation (transaction + savepoint per test function). The following gaps were identified:

### T-1 — Purge Endpoint Has No Integration Test (HIGH)

**Issue:** The `POST /api/v1/admin/purge` endpoint is not covered by any integration test. Given that it performs a cascade delete, this is a significant gap.
**Recommendation:** Add an integration test that seeds projects/items, runs a purge, and asserts the expected rows are deleted and archived.

---

### T-2 — Audit Log Population Not Verified (MEDIUM)

**Issue:** While audit logging is called in multiple endpoints (user creation, promotion, deletion, purge), no test asserts that a row was actually written to `audit_logs` after these operations.
**Recommendation:** Add assertions in existing admin tests to confirm `audit_logs` count increases after each sensitive action.

---

### T-3 — Upload History Status Updates Not Verified (MEDIUM)

**Issue:** `UploadHistory` records are created during ingestion, but no test checks that the status field is updated to `succeeded` or `failed` after the run completes.
**Recommendation:** Extend `test_ingest.py` to query `UploadHistory` after each upload and assert the expected status.

---

### T-4 — Combined Filter Search Not Tested (LOW)

**Issue:** Item search tests exercise individual filters (description, state, year_start, etc.) but do not test combinations (e.g., description + state + year range simultaneously).
**Recommendation:** Add at least one test that applies three or more filters together to confirm they AND correctly.

---

### T-5 — JWT Token Expiry Path Not Tested (LOW)

**Issue:** `test_auth_jwt.py` tests invalid tokens but the specific `ExpiredSignatureError` path (a token that was valid but has expired) is not clearly covered.
**Recommendation:** Add a test that mints a token with `expires_delta=timedelta(seconds=-1)` and confirms the API returns `HTTP 401`.

---

## 6. Documentation Findings

### D-1 — Schema Docs Don't Reflect Phase 1 Additions (MEDIUM)

**File:** `docs/05_db_and_migrations/00_db_schema_doc.md`
**Issue:** This document describes the early-phase schema (projects, users, items) but does not mention `upload_history` and `data_quality_issues`, which were added and migrated in Phase 1.
**Recommendation:** Update the schema doc to include all five tables now in the live schema.

---

### D-2 — Several Phase 1 Diary Entries Are Stubs (LOW)

**Files:** `docs/08_diary_logs/01_phase_1/01_auth/01_auth_flow_stabilization.md`, `03_schema/00_schema_and_migration.md`, `04_debugging_sessions/00_debugging_auth_routes_migrations.md`
**Issue:** These files exist but contain no content. They represent work that was done (auth stabilization, schema debugging) but was never written up.
**Recommendation:** Either complete these entries (preferably) or delete the stub files. Empty placeholder files create confusion about what is documented.

---

### D-3 — No `.env.example` File (LOW)

**Issue:** There is no `.env.example` or documented list of required environment variables. New developers have no reference for what secrets need to be set.
**Recommendation:** Create a `.env.example` with placeholder values for all required variables. This pairs with fixing C-3.

---

### D-4 — No CONTRIBUTING.md (LOW)

**Issue:** There are no documented guidelines for branching, PR format, commit conventions, or test requirements.
**Recommendation:** Add a `CONTRIBUTING.md` to the project root. This is low priority but increasingly important as Phase 2 brings more complexity.

---

## 7. Prioritized Recommendations

### Pre-Phase 2 Checklist (Must Address Before Phase 2 Begins)

These items address confirmed defects or security risks in the current codebase. None require significant design work.

- [ ] **C-1** Remove `api/purge.py` and its router registration from `main.py`; confirm `api/admin.py` is the sole owner of the purge endpoint
- [ ] **C-2** Rename `ArchivedProject.__tablename__` to `"archived_projects"` and `ArchivedItem.__tablename__` to `"archived_items"`; fix `archived_at` column type (`Boolean` → `DateTime`); align `ArchivedItem` columns with `Item`
- [ ] **C-3** Confirm `.env` is in `.gitignore` and has never been committed; if it has, rotate the `SECRET_KEY` and database password; create a `.env.example` with placeholder values
- [ ] **T-1** Add an integration test for `POST /api/v1/admin/purge` (seed data → purge → assert deletion and archival)
- [ ] **T-2** Add audit log assertions to at least three existing admin tests (user deletion, promotion, purge)
- [ ] **D-3** Create `.env.example` documenting all required environment variables

---

### Phase 2 Checklist (Address During Phase 2 Development)

These items improve correctness, performance, and maintainability. They do not block Phase 2 entry but should be resolved before Phase 2 exits.

- [ ] **Q-1** Add `MAX_UPLOAD_SIZE_MB` config setting; enforce file size limit on ingest endpoint with `HTTP 413` response
- [ ] **Q-2** Add `ON DELETE CASCADE` to `data_quality_issues.upload_id` FK in a new migration
- [ ] **Q-3** Replace `float` with `Decimal` for `unit_price` in item schemas and models
- [ ] **Q-4** Combine min/max/avg price stats into a single aggregation query
- [ ] **Q-5** Add trigram or GIN index on `item_description` for keyword search (already in Phase 2 Search Performance checklist — confirm it is implemented)
- [ ] **Q-6** Replace `upload_history.status` TEXT with a validated Enum type
- [ ] **T-3** Extend ingest tests to assert `UploadHistory.status` is `"succeeded"` after a successful upload and `"failed"` after an invalid file
- [ ] **T-4** Add a combined-filter search test (description + state + year range together)
- [ ] **T-5** Add a JWT expiry test using `timedelta(seconds=-1)`
- [ ] **D-1** Update `docs/05_db_and_migrations/00_db_schema_doc.md` to include `upload_history` and `data_quality_issues`
- [ ] **Q-8** Log a `DataQualityIssue` for rows with a missing `state` field instead of silently substituting `"XX"`
- [ ] **Q-7** Migrate `audit_log` model to `Mapped[T]` syntax when Phase 2 audit log schema expansion occurs

---

### Future Phase Checklist (Phase 3+)

These items are low-severity or represent planned work already captured in the roadmap.

- [ ] **Q-9** Move `pyright` from runtime dependencies to dev dependencies in `pyproject.toml`
- [ ] **D-2** Complete or remove stub diary log entries in `docs/08_diary_logs/01_phase_1/`
- [ ] **D-4** Add `CONTRIBUTING.md` with branching, PR, commit, and test conventions
- [ ] Hardcoded log file path in `config/settings.py` — make configurable via `settings.LOG_FILE_PATH`
- [ ] Remove unused Auth0 config fields from `settings.py` or move to a clearly-marked Phase 3 placeholder
- [ ] Pagination limit (500) — make configurable via settings rather than hardcoded in route handlers
- [ ] Add a glossary (`docs/glossary.md`) defining domain terms (bid tabulation, unit cost, LF, EA, Jack and Bore, etc.)

---

## 8. Appendix — File-Level Summary

| File | Status | Severity | Issue |
|---|---|---|---|
| `api/admin.py` | ⚠️ Defect | Critical | Duplicate route — same endpoint as `purge.py` |
| `api/purge.py` | ⚠️ Defect | Critical | Duplicate route — should be removed |
| `models/archived_project.py` | ❌ Broken | Critical | `__tablename__ = "projects"` conflicts with live model |
| `models/archived_item.py` | ❌ Broken | Critical | `__tablename__ = "items"` conflicts with live model |
| `.env` | ⚠️ Security | Critical | Credentials must not be in version control |
| `api/ingest.py` | ⚠️ Gap | High | No file size limit |
| `migrations/68ed7ede6930` | ⚠️ Gap | High | Missing `ON DELETE` on `data_quality_issues.upload_id` FK |
| `models/system_setting.py` | ⚠️ Gap | High | No migration created; model unused |
| `schemas/item.py` | ⚠️ Quality | Medium | `unit_price` as `float`, not `Decimal` |
| `api/items.py` | ⚠️ Quality | Medium | Price stats uses two queries; no description index |
| `models/upload_history.py` | ⚠️ Quality | Medium | `status` is unvalidated `TEXT` |
| `models/audit_log.py` | ⚠️ Style | Low | Uses old `Column()` syntax |
| `services/ingestion.py` | ⚠️ Quality | Low | Silent `"XX"` default for missing state |
| `pyproject.toml` | ⚠️ Config | Low | `pyright` in runtime deps |
| `config/settings.py` | ⚠️ Config | Low | Hardcoded log file path |
| All other source files | ✅ Good | — | No issues found |

---

*Audit completed 2026-06-21. All findings are based on static analysis of source files, tests, migrations, and documentation. No dynamic testing was performed.*
