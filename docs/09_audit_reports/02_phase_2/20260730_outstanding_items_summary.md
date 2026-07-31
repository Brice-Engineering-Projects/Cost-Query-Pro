# Cost Query Pro - Outstanding Audit Items Summary

**Date:** 2026-07-30
**Scope:** Consolidated summary of outstanding items from Phase 1 and Phase 2 audit reports, cross-checked against current implementation.

---

## Executive Summary

The codebase is generally stable, but several audit findings remain open. The highest-risk items are still centered on authentication hardening, archived-model schema conflicts, and irreversible purge behavior. Testing and CI quality gaps also remain in key areas.

---

## Outstanding Items by Severity

## CRITICAL

1. **P2-C-2 - Insecure JWT secret defaults remain active**
- `secret_key` still defaults to `"default_secret_key"`.
- `environment` still defaults to `"production"`.
- Risk: token forgery if deployment does not set a strong `SECRET_KEY`.

2. **C-2 - Archived model table-name collisions still unresolved**
- `ArchivedProject.__tablename__ = "projects"` and `ArchivedItem.__tablename__ = "items"` still conflict with live models.
- `ArchivedProject.archived_at` still uses `Boolean` instead of a timestamp.
- No archive-table migration has been added.

3. **Test false assurance - revoked user test still tautological**
- `test_revoked_user_rejected` still asserts a hardcoded logical path, not endpoint behavior.
- This remains a known false-confidence test in auth/JWT coverage.

## HIGH

4. **P2-C-1 - Purge remains irreversible**
- Purge endpoint still performs hard deletes and commit without writing archive rows.
- Archive flow remains blocked by unresolved archived-model/migration defects.

5. **JWT missing-sub test does not validate API behavior**
- `test_missing_sub_claim` still checks token decoding only, not protected-route rejection.

6. **Ingestion endpoint lacks file-size limit enforcement**
- No configured max upload size check (`HTTP 413` path still missing).

7. **Missing ON DELETE CASCADE for `data_quality_issues.upload_id`**
- FK still lacks explicit cascade behavior and may leave orphaned rows.

## MEDIUM

8. **P2-M-2 - Coverage tooling still not wired for active dev sync path**
- `pytest-cov` remains outside the dependency group used by `uv sync --dev`.
- Coverage config exists but is not reliably executable in standard dev/CI setup.

9. **Missing `alembic check` CI gate**
- CI runs mypy/migrations/tests but still does not include migration-drift gate.

10. **Ingestion still uses `"XX"` fallback for invalid/missing state**
- Sentinel fallback remains in ingestion logic instead of emitting structured data-quality handling.

11. **Upload status remains unvalidated free text**
- Status is still not constrained to the roadmap state machine values.

## LOW

12. **Missing `.env.example`**
- `.env` is ignored, but there is still no committed `.env.example` for onboarding and secret-shape documentation.

---

## Previously Reported Items That Appear Closed

1. Duplicate purge route registration (C-1) no longer appears duplicated in router wiring.
2. `.env` is gitignored and not currently tracked.

---

## Recommended Immediate Remediation Order

1. **P0 Security:** Enforce required strong `SECRET_KEY` and remove insecure defaults.
2. **P0 Data Safety:** Fix archived models + add migrations, then implement transactional purge-to-archive.
3. **P1 Test Integrity:** Replace tautological JWT tests with endpoint-level assertions.
4. **P1 Governance:** Add `alembic check` and coverage wiring in CI/developer dependency path.
5. **P2 Reliability:** Add ingest size limits, FK cascade fix, and state/status validation hardening.
