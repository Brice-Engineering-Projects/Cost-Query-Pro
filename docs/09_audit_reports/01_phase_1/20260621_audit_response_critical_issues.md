# 20260621_audit_response_critical_issues

## Critical Issues

### 1. Executive Summary

Cost Query Pro Phase 1 delivers a working FastAPI backend with JWT authentication, a stable PostgreSQL schema, a structured item search API, and a CSV/Excel ingestion pipeline. The codebase is well-organized, the test suite is solid, and the documentation is above average for an early-stage project.

**Three critical defects block Phase 2 entry:**

1. A duplicate route registration for `POST /api/v1/admin/purge` (both `api/admin.py` and `api/purge.py` register the same endpoint) creates undefined routing behavior.
2. Two archived models (`ArchivedProject`, `ArchivedItem`) declare `__tablename__` values that conflict with the live `projects` and `items` tables, which will cause a SQLAlchemy registry crash if those models are ever instantiated.
3. The `.env` file containing database credentials and the JWT secret key appears to be tracked in version control.

All three must be resolved before Phase 2 development begins. The remaining findings are lower-severity issues that can be addressed within Phase 2 or deferred further.

### Response

1. The purpose of the `POST /api/v1/admin/purge` endpoint is to allow the admin user to delete data with certain criteria from the database.  For example, the endpoint can be used to delete all projects created before a certain date, or all items with a certain status. This endpoint is useful to keep the database current and up-to-date.

  * The purge endpoint was meant to be the mechanism for admin users to delete data from the database.
  * The idea of the purge endpoint was to eventually be the mechanism that could be used in the future  as a way to clean the database with automated scripts.
  * If the concept can be kept, then move forward with your recommendation to delete the purge endpoint.
  * If the concept cannot be kept, then provide a recommendation for a different approach.

2. I agree with your recommendation -> **Fix (Phase 2):** Rename tables to `archived_projects` and `archived_items`, correct `archived_at` to `DateTime`, align columns with source models, and create migrations. The roadmap correctly tracks this as `[!]` blocked.

3. The `.env` file is not tracked in version control.


> Other findings in the audit report will be looked at and discussed later.
