# Cost Query Pro — Mypy Strict-Mode Remediation Audit

**Date:** 2026-07-27
**Branch:** `phase_2`
**Auditor:** Claude Opus 5
**Scope:** The 10-commit strict-typing remediation (`7d78419..HEAD`), its behavioural impact, and the surrounding quality gates
**Verdict:** Remediation is complete and verified. Two defects were found and fixed during the work that were not typing issues at all. The audit itself surfaced **one CRITICAL pre-existing security defect** unrelated to the remediation, which should be triaged before Phase 3.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope and Method](#2-scope-and-method)
3. [Verification Results](#3-verification-results)
4. [Remediation Assessment](#4-remediation-assessment)
5. [Behavioural Impact Analysis](#5-behavioural-impact-analysis)
6. [New Findings](#6-new-findings)
7. [Status of Prior Audit Findings](#7-status-of-prior-audit-findings)
8. [Prioritised Recommendations](#8-prioritised-recommendations)
9. [Appendix A — Commit Inventory](#9-appendix-a--commit-inventory)
10. [Appendix B — Reproducing This Audit](#10-appendix-b--reproducing-this-audit)

---

## 1. Executive Summary

The remediation removed all 70 `mypy --strict` errors across 23 files without weakening type checking, and the behavioural baseline held: 165 tests passing before, 171 passing after, with the six additional tests covering code the change touched.

Three things are worth the reader's attention more than the error count.

**Two of the 70 "typing errors" were real defects.** The Starlette findings in `web/views/routes.py` were not typing debt. Starlette 1.0 removed the legacy `TemplateResponse(name, context)` call form, so `GET /dashboard` raised `TypeError: unhashable type: 'dict'` on **every** request under the upgraded dependency. The route had no test coverage, which is how the break survived the security upgrade. Separately, `tests/unit_tests/test_auth_jwt.py` imported from `src.cost_query_pro.*`, creating a second `Base` in the interpreter with an empty `MetaData`.

**Nothing was enforcing any of this.** Neither CI workflow ran mypy, the pre-commit mypy hook was commented out, and the `[mypy]` section in `setup.cfg` was read by nothing — mypy stops at `pyproject.toml`, whose `[tool.mypy]` block still carried a set of "temporary relaxations". The 70 errors could have returned silently. A CI type gate now exists in both workflows.

**The audit found a CRITICAL defect outside the remediation's scope.** `Settings.secret_key` defaults to the literal string `"default_secret_key"` and `Settings.environment` defaults to `"production"`. A deployment that does not set `SECRET_KEY` signs JWTs with a value published in this repository. This is pre-existing, unrelated to the typing work, and detailed as **P2-C-2** below.

---

## 2. Scope and Method

**In scope:** the 9 remediation commits in `7d78419..HEAD` — 30 files, +387/−92:

| Area | Files | Change |
|---|---|---|
| `src/` | 20 | +133 / −71 |
| `tests/` | 5 | +164 / −10 |
| `migrations/` | 1 | +57 |
| Build & CI | 5 | +66 / −20 |

The range also contains one commit not authored by the remediation (`3b98720`, the
instructions document plus the Starlette `1.0.1` and pyasn1 dependency bumps and lockfile).
Those bumps are the *premise* of this work rather than part of it — the Starlette major
upgrade is what exposed the defect in §4 — so they are treated as the baseline, not as a
change under review.

**Method:** the five gates from the remediation instructions, plus independent verification of every behavioural claim the remediation made — OpenAPI document diffing, Alembic drift and round-trip checks, module-identity probes, and a warnings census. Claims were verified against the pre-remediation commit rather than accepted from the change description.

**Environment:** Python 3.12.3 · mypy 2.1.0 · FastAPI 0.140.0 · Starlette 1.3.1 · SQLAlchemy 2.0.51 · Pydantic 2.13.4 · PostgreSQL (local test database)

**Not in scope:** application logic not touched by the remediation, the agent pipeline's prompt behaviour, and Phase 3 deployment concerns. Findings outside scope are recorded where the audit encountered them but were not systematically hunted.

---

## 3. Verification Results

| Gate | Before | After | Status |
|---|---|---|---|
| `ruff check .` | pass | pass | ✅ |
| `black --check .` | pass (84 files) | pass (86 files) | ✅ |
| `mypy --strict src/cost_query_pro` | **70 errors / 23 files** | **0 errors / 53 files** | ✅ |
| `mypy .` (whole repo) | not runnable¹ | 0 errors / 77 files | ✅ |
| `pytest` | 165 passed | **171 passed** | ✅ |
| `pip-audit` | clean | clean | ✅ |
| `alembic check` | **FAILED (drift)** | no new operations | ✅ |
| `pre-commit run --all-files` | 9/9 | 9/9 | ✅ |
| Test warnings | 127 | 127 | ✅ |

¹ Aborted with `Source file found twice under different module names` until the `src.`-prefixed import was corrected.

### Error reduction by category

| Category | Count | Resolution |
|---|---|---|
| Missing annotations (`no-untyped-def`) | 57 | Concrete types added; no `Any` used as a shortcut |
| `Class cannot subclass "Base"` | 10 | Fixed once at the declarative base |
| Pydantic `prop-decorator` | 4 | Narrow, documented suppression (see §4) |
| Generic `dict` without parameters | 3 | `TypedDict` where the contract is known; `dict[str, Any]` only at genuine JSON/SDK boundaries |
| Starlette `TemplateResponse` arg types | 2 | **Real runtime defect** — see §4 |
| Unused `type: ignore` | 2 | Removed, not broadened |
| Unknown callable / `Any` propagation | 2 | Fixed at the boundary where type information was lost |
| Non-exported import | 2 | Imported from the defining module |

---

## 4. Remediation Assessment

### Compliance with the remediation instructions

| Requirement | Assessment |
|---|---|
| No global mypy strictness weakened | ✅ Strictness was **increased** — `strict = true` now in config, relaxations removed |
| No unnecessary `Any` introduced | ✅ 9 occurrences, each at a JSON, JWT-claim, or SDK-kwargs boundary, each commented |
| No broad `# type: ignore` added | ✅ 4 added, all `[prop-decorator]`, all documented |
| Existing FastAPI behaviour unchanged | ✅ Verified by OpenAPI diff — see §5 |
| Existing SQLAlchemy/Alembic behaviour unchanged | ✅ Same 7 tables, same naming convention; `alembic check` output identical pre/post for the base change |
| API contracts unchanged | ⚠️ Three response **schemas** newly documented; payloads byte-identical — see §5 |
| All existing tests pass | ✅ 165 → 171 |
| New tests where behaviour changed | ✅ 6 added |
| Python version unchanged | ✅ 3.12 |
| Architecture preserved | ✅ `src/` layout intact; one `src.`-prefixed import **removed** per instruction §1 |

### Judgement calls, with the reasoning

**The four `prop-decorator` suppressions are justified.** Instruction §7 permits suppression only for a documented incompatibility that cannot reasonably be resolved. mypy cannot represent a decorator stacked on `@property` — [mypy #1362](https://github.com/python/mypy/issues/1362), open upstream. Pydantic's own `computed_field` docstring prescribes `# type: ignore[prop-decorator]` for exactly this case, and explicitly discourages the alternative of dropping `@property` ("you will lose IntelliSense in your IDE, and confuse static type checkers"). The suppressions carry the specific error code and an in-file comment, satisfying all four conditions of instruction §11.

**Instruction §2 rested on a false premise, and was followed in spirit rather than to the letter.** The instructions state that duplicate-module discovery was resolved by `explicit_package_bases = true` in `setup.cfg`, and direct that it not be reverted. That setting was never active: mypy resolves configuration in the order `mypy.ini`, `.mypy.ini`, `pyproject.toml`, `setup.cfg` and stops at the first file found, so a `[mypy]` section in `setup.cfg` is dead config in a project that has `[tool.mypy]` in `pyproject.toml`. Discovery worked because of the `src/` layout. The setting was moved to `pyproject.toml`, where it now genuinely earns its place by making whole-repository runs work, and `setup.cfg` retains a comment so the dead config is not recreated.

### Defects fixed that were not typing issues

**D-1 — `GET /dashboard` was broken in production.** Under Starlette 1.x the legacy call form binds the template name to the `request` parameter and the context dict to `name`, then passes the dict to `get_template()`. Confirmed directly:

```
TypeError: unhashable type: 'dict'
```

Every request to the dashboard would have failed. The route had zero coverage. Fixed to `TemplateResponse(request, name, context)` and covered by three tests in `tests/unit_tests/test_web_views.py`.

**D-2 — a duplicate `Base` existed whenever `test_auth_jwt.py` was imported.** The prior test-file audit flagged this import as HIGH, and was right to, but its stated mechanism was incorrect. Measured:

| Object | Same across `cost_query_pro.*` and `src.cost_query_pro.*`? |
|---|---|
| `models.User` class | **Yes** — same object |
| `db.Base` | **No** — distinct classes |
| `Base.metadata` table count | **7 vs 0** |

`models/__init__.py` re-exports via absolute imports, so `User` was never duplicated as the prior audit described. `db/__init__.py` uses a *relative* import, so the second namespace produced a second declarative base carrying an **empty** `MetaData`. Any use of that object for `create_all()` or as an Alembic target would have produced an empty schema. The import is corrected; the hazard is gone.

---

## 5. Behavioural Impact Analysis

### OpenAPI: no contract change, three schemas newly documented

The generated OpenAPI document was diffed against the pre-remediation commit after **all** commits:

- Routes added or removed: **none**
- Status codes changed: **none**
- Request bodies changed: **none**
- Response schemas changed: **three**

The three are endpoints that previously declared neither `response_model` nor a return annotation, and so published an empty `{}` schema. FastAPI now infers one from the return annotation:

| Endpoint | Before | After |
|---|---|---|
| `GET /` | `{}` | `object` |
| `DELETE /api/v1/admin/purge` | `{}` | `object` |
| `DELETE /api/v1/admin/users/{user_id}` | `{}` | `object` with string values |

Response payloads are byte-identical; this documents schemas that were previously blank. It is a visible change to the published document and is flagged rather than buried. If strict document stability is required, adding `response_model=None` to those three routes restores the empty schema at the cost of the documentation.

### Database: metadata and migration behaviour preserved

Replacing `declarative_base()` with a `DeclarativeBase` subclass is runtime-inert — the same 7 tables, the same `{'ix': 'ix_%(column_0_label)s'}` naming convention, no schema. `alembic check` produced identical output before and after the change, confirming the autogenerate target is unchanged.

Migration `a3f5c81e7b24` was verified through a full `upgrade → downgrade → upgrade` cycle with the `server_default` preserved at each step.

### One behavioural change was intended

`llm_usage.created_at` is now `NOT NULL`. Rationale is in §6 (**P2-M-1**, closed).

---

## 6. New Findings

### Severity key

| Severity | Meaning |
|---|---|
| **CRITICAL** | Exploitable or causes data loss; fix before further deployment |
| **HIGH** | Material defect or a governance claim that is untrue |
| **MEDIUM** | Real gap that will cause avoidable failures |
| **LOW** | Hygiene; no functional impact |

---

### P2-C-2 — Hardcoded default JWT signing key, defaulting to a production environment (CRITICAL)

**File:** `src/cost_query_pro/config/settings.py:77`
**Status:** OPEN · pre-existing · **outside the remediation's scope**

```python
class Settings(BaseSettings):
    secret_key: str = Field("default_secret_key")
    environment: str = Field("production")
```

Measured in a clean environment with no variables set:

```
secret_key   : 'default_secret_key'
length       : 18 bytes  (RFC 7518 minimum for HS256 = 32)
environment  : 'production'
algorithm    : 'HS256'
```

**Impact.** A deployment that fails to set `SECRET_KEY` signs and validates JWTs with a string published in this repository. Anyone able to read the repo can forge a token for any username with `is_admin: true` and obtain full administrative access, including the irreversible purge endpoint. The failure is silent: there is no startup error, no warning, and `environment` simultaneously reports `"production"`.

There is also no length validation on the field. Even when `SECRET_KEY` *is* supplied, the current test environment's 20-byte key trips PyJWT's `InsecureKeyLengthWarning` (below the 32-byte RFC 7518 minimum for HS256) on every token operation — 3 distinct call sites across the suite.

**Recommended fix.** Remove the default so the field is required, and validate length at startup:

```python
secret_key: str = Field(..., min_length=32)
```

A missing or short secret should abort startup rather than fall back. Consider also defaulting `environment` to `"development"`, so that an unconfigured deployment fails safe rather than silently claiming to be production.

**Note.** This is unrelated to the typing remediation and was surfaced by the warnings census in this audit. It is recorded here because it is the most severe issue currently known in the codebase.

---

### P2-C-1 — Admin purge is irreversible; archival was marked complete but is not implemented (HIGH)

**Files:** `src/cost_query_pro/api/purge.py`, `models/archived_project.py`, `models/archived_item.py`
**Status:** OPEN · tracked in the roadmap · blocked on Phase 1 finding **C-2**

The roadmap line `- [x] Purged data archived to archived_projects and archived_items` was marked done. It is not implemented:

- `api/purge.py` deletes items and projects outright and never writes an archive row
- `ArchivedProject` / `ArchivedItem` are not imported in `models/__init__.py`, so they are absent from `Base.metadata`
- No migration creates the destination tables — they do not exist in any environment

Admin purge is therefore **irreversible**, which is the opposite of what the checklist claimed. The line has been re-marked `[!]` and tracked as **P2-C-1**.

It is blocked on Phase 1 **C-2**: the models cannot be used until their table-name collisions are fixed. Verified during this audit:

```
InvalidRequestError: Table 'projects' is already defined for this MetaData instance.
```

**Recommended fix (after C-2).** Write archive rows inside the same transaction as the delete, so a failed archive aborts the purge rather than losing data silently; record `purged_by_user_id` and the archive timestamp; and cover with a test asserting purged rows are recoverable.

---

### P2-M-1 — `llm_usage.created_at` model/migration drift (MEDIUM) — **CLOSED**

**Status:** FIXED in this branch (`a3f5c81e7b24`)

The model declared `created_at: Mapped[datetime]` — non-Optional, therefore `NOT NULL` in `Base.metadata` — while migration `c7a4e2b91d38` created the column nullable. `alembic check` failed on the drift.

Two reasons this mattered beyond tidiness. It was a trap: the next `alembic revision --autogenerate` would have silently folded a spurious `modify_nullable` into whatever else it carried. And `created_at` is the window column for the Phase 2 cost controls — rate limits `COUNT` over a time window, the spend cap `SUM`s over the calendar month. A NULL never satisfies a range predicate, so an untimestamped row would drop out of both, under-reporting spend and letting requests past the limit. `NOT NULL` is the constraint that makes those aggregates trustworthy, and Step 2 of the cost-control work builds directly on this table.

Backfill was a no-op (the column has carried `server_default now()` since creation), but the migration includes a defensive `UPDATE`.

---

### P2-M-2 — Coverage tooling is configured but cannot run (MEDIUM)

**Files:** `pyproject.toml:48`, `setup.cfg:54-66`
**Status:** OPEN

`pytest-cov` is declared only in `[project.optional-dependencies].dev`. uv installs from `[dependency-groups].dev`, which does not include it, so `uv sync --dev` does not provide it:

```
$ uv run pytest --cov=cost_query_pro
ERROR: unrecognized arguments: --cov=cost_query_pro
```

`setup.cfg` carries `[coverage:run]` and `[coverage:report]` sections that nothing can use. Coverage is currently unmeasurable and consequently ungated — including for the six tests this branch added.

**Recommended fix.** Move `pytest-cov` into `[dependency-groups].dev`, then decide whether coverage should gate CI or merely report.

---

### P2-M-3 — Starlette test client will require `httpx2` (MEDIUM)

**Status:** OPEN · forward-looking

The Starlette 1.x upgrade emits:

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated;
install `httpx2` instead.
```

The entire test suite runs through `fastapi.testclient.TestClient`. This is a warning today and will become a break in a future Starlette release. Given that the last Starlette major upgrade silently broke an uncovered route (**D-1**), this one is worth scheduling rather than absorbing unplanned.

---

### P2-L-1 — Finding ID namespace collision (LOW) — **CLOSED**

Introduced and fixed within this audit. Roadmap `[C-n]` markers refer to Phase 1 audit finding IDs. A new item was initially filed as `[C-3]`, colliding with Phase 1's C-3 (*Credentials in Version Control*). Renamed to `[P2-C-1]`. Future Phase 2 findings should use the `P2-` prefix.

---

### P2-L-2 — Test-isolation warning introduced and resolved (LOW) — **CLOSED**

A test added in this branch triggered `SAWarning: transaction already deassociated from connection` at `conftest.py:154`, because an expected `IntegrityError` poisoned the fixture's outer transaction. Resolved by running the failing statement inside its own `SAVEPOINT`. Warning count is back to the 127 baseline.

This is a concrete instance of the prior test audit's MEDIUM finding on savepoint-restart reliability (§7), which remains open.

---

## 7. Status of Prior Audit Findings

### Phase 1 audit (`20260621_audit_report.md`)

| ID | Finding | Status |
|---|---|---|
| C-1 | Duplicate purge route registration | ✅ **Remediated** — `api/admin.py` removed; `api/purge.py` is the sole implementation |
| C-2 | Archived model table-name conflicts | ❌ **Open** — re-verified this audit; raises `InvalidRequestError`. Blocks P2-C-1 |
| C-3 | Credentials in version control | ✅ **Remediated** — `.env` untracked and covered by `.gitignore` |

### Phase 2 test-file audit (`20260624_test_file_audit_report.md`)

| Finding | Status |
|---|---|
| HIGH — `test_auth_jwt.py` import inconsistency | ✅ **Fixed in this branch.** Note the mechanism differed from the original description — see **D-2** |
| CRITICAL — `test_revoked_user_rejected` is a false test | ❌ **Open.** Re-verified: `user.is_admin = False` followed by `if not user.is_admin: access_granted = False` then `assert not access_granted` remains tautological |
| HIGH — `test_missing_sub_claim` tests PyJWT, not the app | ❌ Open |
| MEDIUM — savepoint restart may be unreliable | ❌ Open — encountered in practice this branch (**P2-L-2**) |
| MEDIUM — expiration/signature tests are library-level | ❌ Open |

---

## 8. Prioritised Recommendations

| # | Action | Severity | Effort |
|---|---|---|---|
| 1 | Make `SECRET_KEY` required with `min_length=32`; default `environment` to `development` (**P2-C-2**) | CRITICAL | Small |
| 2 | Fix Phase 1 **C-2** archived models, then implement **P2-C-1** purge-to-archive in one transaction | HIGH | Medium |
| 3 | Replace the tautological `test_revoked_user_rejected` with an endpoint-level assertion | HIGH | Small |
| 4 | Move `pytest-cov` to `[dependency-groups].dev` and decide on a coverage gate (**P2-M-2**) | MEDIUM | Small |
| 5 | Add `alembic check` to the CI test gate so drift fails the build rather than the next autogenerate | MEDIUM | Small |
| 6 | Schedule the `httpx2` migration for the test client (**P2-M-3**) | MEDIUM | Medium |
| 7 | Raise `tests/` to strict typing and drop the `[[tool.mypy.overrides]]` relaxation (~230 findings, nearly all missing annotations on test functions) | LOW | Medium |

All seven are tracked in `docs/07_checklist/00_high_level_roadmap.md` as of this audit:
items 1 and 3 under *Authentication Enhancements* (Phase 2), item 2 under *Admin Operations
and Data Governance* and *Schema Continuations*, and items 4–7 under *Deployment and CI/CD*.

---

## 9. Appendix A — Commit Inventory

| Commit | Subject | Category |
|---|---|---|
| `21ec50b` | `fix(web)` Starlette 1.x TemplateResponse convention | **Defect fix** |
| `d704965` | `refactor(db)` modernize SQLAlchemy declarative base typing | Typing |
| `1012f69` | `refactor` add type annotations to API, main, db, model layers | Typing |
| `9e50ef2` | `refactor` strengthen service and core typing | Typing |
| `1739c87` | `fix(schemas)` annotate Pydantic computed fields | Typing |
| `5d865d9` | `refactor` import auth dependency from its defining module | Typing |
| `f9e4354` | `fix(db)` make `llm_usage.created_at` NOT NULL | **Defect fix** |
| `fe38499` | `build` consolidate mypy config and enforce it in CI | Infrastructure |
| `51ea269` | `docs(checklist)` correct purge-archive status, record type gate | Documentation |

Commits are scoped by category; no single "fix mypy" commit was produced, per instruction §14.

### Tests added (6)

| File | Tests | Covers |
|---|---|---|
| `tests/unit_tests/test_web_views.py` | 3 | Dashboard render, context propagation, auth requirement (**D-1**) |
| `tests/unit_tests/test_usage_recorder.py` | 3 | `created_at` NOT NULL in the migrated schema, server default, NULL rejection (**P2-M-1**) |

---

## 10. Appendix B — Reproducing This Audit

```bash
# Gates
uv run ruff check .
uv run black --check .
uv run mypy --strict src/cost_query_pro     # the CI gate
uv run mypy .                               # whole repo
uv run pytest -q
uv run pip-audit
uv run pre-commit run --all-files

# Migration drift and round-trip
export TEST_DATABASE_URL=...
uv run alembic check
uv run alembic downgrade -1 && uv run alembic upgrade head

# Warnings census (setup.cfg sets --disable-warnings by default)
uv run pytest -q --override-ini="addopts=" -W always

# Default-configuration probe for P2-C-2
env -i PATH="$PATH" PYTHONPATH=src .venv/bin/python -c \
  "from cost_query_pro.config.settings import Settings; s=Settings(); \
   print(repr(s.secret_key), len(s.secret_key), repr(s.environment))"
```

**Note on the warnings census.** `setup.cfg` sets `addopts = --disable-warnings`, so a default `pytest` run hides the warning summary. Overriding it is what surfaced **P2-C-2** and **P2-M-3**. This is worth doing periodically.

---

*End of report.*
