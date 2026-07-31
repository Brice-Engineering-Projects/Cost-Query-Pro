# Cost Query Pro - Outstanding Audit Items Checklist

**Date:** 2026-07-30
**Purpose:** Actionable checklist of open audit findings, mapped to roadmap and audit IDs.

---

## P0 - Critical (Do First)

- [x] **P2-C-2** Require strong JWT secret and remove insecure defaults
  - [x] Set `secret_key` to required with minimum length validation
  - [x] Remove hardcoded fallback value `default_secret_key`
  - [x] Fail startup when secret is missing/weak
  - [x] Consider defaulting environment to safer non-production baseline
  - **Evidence (2026-07-30):** Updated `src/cost_query_pro/config/settings.py` to require `SECRET_KEY` with `min_length=32` and changed default `environment` to `development`; updated CI secrets in `.github/workflows/ci.yml` and `.github/workflows/ci-cd.yml` to satisfy the new minimum length.
  - **References:** roadmap P2-C-2, mypy remediation audit (2026-07-27)

- [ ] **C-2** Fix archived model/table conflicts and schema defects
  - [ ] Rename `ArchivedProject.__tablename__` to `archived_projects`
  - [ ] Rename `ArchivedItem.__tablename__` to `archived_items`
  - [ ] Change archived timestamp field to DateTime semantics
  - [ ] Align archived item columns with live item shape (including upload lineage where required)
  - [ ] Add migration(s) for archived tables and constraints
  - **References:** phase 1 audit C-2, roadmap C-2

- [ ] **JWT test integrity (CRITICAL)** Replace tautological revoked-user test
  - [ ] Remove/replace `test_revoked_user_rejected` false-positive logic
  - [ ] Add endpoint-level auth rejection test tied to real user-state control
  - **References:** phase 2 test-file audit (2026-06-24), roadmap auth enhancements

---

## P1 - High Priority

- [ ] **P2-C-1** Make purge recoverable (transactional purge-to-archive)
  - [ ] Write archive rows in same transaction as delete
  - [ ] Abort purge if archival write fails
  - [ ] Add integration test proving recoverability from archive tables
  - **Blocked by:** C-2
  - **References:** roadmap P2-C-1, mypy remediation audit (2026-07-27)

- [ ] Replace JWT missing-sub test with endpoint behavior assertion
  - [ ] Submit token without sub claim to protected route
  - [ ] Assert 401/403 response contract
  - **References:** phase 2 test-file audit (2026-06-24)

- [ ] Add ingestion upload-size guardrail
  - [ ] Add configurable max upload size setting
  - [ ] Reject oversized uploads with HTTP 413
  - [ ] Add tests for over-limit payloads
  - **References:** phase 1 audit Q-1

- [ ] Add ON DELETE CASCADE for `data_quality_issues.upload_id`
  - [ ] Update model FK behavior
  - [ ] Add migration for FK policy change
  - [ ] Add regression test for orphan-prevention behavior
  - **References:** phase 1 audit Q-2

---

## P2 - Medium Priority

- [ ] **P2-M-2** Fix coverage tooling path
  - [ ] Move `pytest-cov` into dependency group used by `uv sync --dev`
  - [ ] Validate `--cov` works in local and CI flows
  - [ ] Decide/report coverage gate threshold policy
  - **References:** roadmap P2-M-2, mypy remediation audit (2026-07-27)

- [ ] Add `alembic check` to CI gate
  - [ ] Add explicit migration-drift step in CI workflows
  - [ ] Fail pipeline on model/migration drift
  - **References:** roadmap CI/CD section

- [ ] Remove silent `XX` state fallback in ingestion
  - [ ] Replace sentinel fallback with structured data-quality handling
  - [ ] Add clear issue records and error semantics
  - **References:** phase 1 audit Q-8

- [ ] Constrain upload history status lifecycle
  - [ ] Replace free-text status with validated enum/state machine
  - [ ] Align states with roadmap (`queued`, `running`, `succeeded`, `failed`)
  - [ ] Add tests for valid/invalid state transitions
  - **References:** phase 1 audit Q-6, roadmap ingestion reliability

- [ ] **P2-M-3** Plan migration away from deprecated Starlette TestClient/httpx pairing
  - [ ] Define migration approach and impact window
  - [ ] Execute and validate full test-suite compatibility
  - **References:** roadmap P2-M-3, mypy remediation audit (2026-07-27)

---

## P3 - Low Priority / Hygiene

- [ ] Add `.env.example` with required variable placeholders
  - [ ] Document required auth/db/llm settings
  - [ ] Keep secrets out of repository while documenting expected keys
  - **References:** phase 1 audit D-3

---

## Verification Checklist (Use After Each Remediation PR)

- [ ] Unit/integration tests added or updated for the changed behavior
- [ ] Migrations include downgrade paths
- [ ] CI passes with no new warnings/errors
- [ ] Roadmap item status updated with date and evidence
- [ ] Audit trail note added under `docs/09_audit_reports/02_phase_2/`
