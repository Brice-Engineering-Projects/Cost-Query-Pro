# Cost Query Pro - Roadmap Checklist

Cost Query Pro centralizes historical bid tabulation data (CSV, Excel, PDF) from infrastructure projects and makes it queryable through a structured API and a natural language AI agent. Engineers and estimators ask plain-English cost questions and get answers backed by cited project records.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · Claude API (AI agent, primary) · OpenAI API (AI agent, fallback)

---

## Global Standards

### Checklist Legend

| Symbol | Meaning |
|--------|---------|
| `[x]` | **Done** — implemented, tested, and documented |
| `[ ]` | **Pending** — not yet started |
| `[~]` | **In progress** — actively being worked |
| `[>]` | **Deferred** — intentionally postponed to a later phase |
| `[!]` | **Blocked** — cannot proceed; dependency or decision required |
| `[-]` | **Dropped** — removed from scope; not planned |

**Finding IDs.** Bare `[C-n]` markers refer to findings in the Phase 1 audit
(`docs/09_audit_reports/01_phase_1/`). Findings raised by Phase 2 audits use a `P2-`
prefix (`[P2-C-1]`, `[P2-C-2]`, …) so the two numbering schemes cannot collide.

### Completion Criteria

A work item is complete (`[x]`) only when:

- [ ] Code implemented and peer reviewed
- [ ] Unit and/or integration tests added or updated
- [ ] Migrations applied with rollback path validated
- [ ] API contract documented (OpenAPI or inline)
- [ ] Logging and error handling in place
- [ ] Security and authorization checks verified
- [ ] `docs/` updated if behavior changed

**Release gate for each phase:** target user workflows pass end-to-end · no P1/P2 open defects · auth/authorization reviewed · ingestion validation thresholds met · logs and health checks documented

---

## Phase 1 — Foundation MVP

**Delivers:** A working backend with secure authentication, stable schema, structured cost search API, and a CI pipeline. The system can store and query historical cost records. Ingestion from files is the remaining gap.

**Status:** Largely complete. Remaining gaps are noted below.

### Authentication

- [x] Password hashing with bcrypt (direct — passlib removed)
- [x] JWT access tokens (HS256, configurable expiration)
- [x] `get_current_user` and `get_current_admin` shared dependencies
- [x] Login (form + JSON), register, and `/me` endpoints
- [x] Admin-only routes blocked for non-admin users
- [x] Password minimum length enforced at registration (configurable via `PASSWORD_MIN_LENGTH`, default 8)
- [x] Auth test coverage: register · login (form + JSON) · wrong password · duplicate username · /me · expired token · invalid signature · missing claim · revoked user · admin/non-admin enforcement · short password rejected
- [>] Refresh token flow — deferred to Phase 3
- [>] Login throttling / lockout after repeated failures — deferred to Phase 3
- [>] `role_permissions` bridge table for true RBAC — deferred to Phase 2 (binary `is_admin` covers Phase 1)
- [>] Seed baseline roles and permissions — deferred to Phase 2

### Schema and Migrations

- [x] Core entities migrated: `users`, `projects`, `items`, `audit_logs`
- [x] `upload_history` and `data_quality_issues` models fixed (Mapped[T], corrected FK refs) and migrated — migration 68ed7ede6930
- [!] `archived_projects`, `archived_items`, `system_settings` model bugs remain — deferred to Phase 2
- [x] Five ordered migrations: initial schema → quantity column → audit logs → check constraints → ingest models + upload lineage
- [x] `alembic upgrade head` runs in CI as a smoke test
- [x] Fresh database reproducible from migrations with no manual steps
- [x] Downgrade functions present in all migrations (drop column / drop table / drop constraint)
- [x] Check constraints enforced in DB and model: `unit_price >= 0`, `quantity >= 0` on `items`
- [x] Canonical ERD and schema documentation in `docs/05_db_and_migrations/00_schema/` (PDF + markdown)
- [>] `users.email` column and unique constraint — deferred to Phase 2
- [>] `roles` and `permissions` tables — deferred to Phase 2 (part of RBAC)
- [>] FK naming consistency review and referential action documentation — deferred to Phase 2
- [>] Fix model bugs in `UploadHistory`, `DataQualityIssue`, `ArchivedProject`, `ArchivedItem` and write their migrations — deferred to Phase 2

### Core API

- [x] Project endpoints: create, read, update, delete, list (state/year filter), items-by-project
- [x] Item endpoints: create, read, update, delete, search (8 filter types), distinct units, price-range stats
- [x] Admin endpoints: list users, delete user, promote user, purge data by year cutoff
- [x] Pydantic request/response validation on all public endpoints
- [x] Pagination on all list/search routes (skip/limit, max 500)
- [x] Health check at `/` (returns DB connectivity status)
- [x] Deterministic sort order on all paginated responses
- [x] Structured API-level error codes for client troubleshooting (`AppError` + global handler, Option B)
- [x] Duplicate `/search` route definition in `items.py` removed/consolidated
- [x] **[C-1]** Consolidate duplicate purge endpoint: retain `api/purge.py` implementation (structured `AppError`, admin username audit logging); remove the purge handler from `api/admin.py` and its duplicate router registration from `main.py`
- [>] OpenAPI docs verified accurate for all implemented behavior — deferred; requires live app review

### Ingestion Pipeline (CSV / Excel / PDF)

*CSV and Excel supported. PDF deferred. Models fixed, migrated, and fully tested.*

- [x] File upload endpoint: `POST /api/v1/ingest/upload`
- [x] Canonical import schema defined (required columns: `project_number`, `item_description`, `unit`, `unit_price`, `quantity`)
- [x] File-level validation: type check (csv/xlsx), required header presence → `INGEST_MISSING_COLUMNS`
- [x] Row-level validation: numeric fields, non-negative values; per-row error isolation
- [x] Column header normalization: case-insensitive match (strip + lowercase)
- [x] Structured ingest report per run: inserted · skipped · failed + per-row issue list
- [>] PDF table extraction via pdfplumber — deferred to Phase 2; must extract `project_number` from page-level footer/header metadata as well as table columns, since project numbers frequently appear only in the document footer on PDF bid tabulations
- [x] Idempotency: composite key `(project_number, item_description, unit)` — duplicates skipped
- [x] Ingestion lineage stored: `UploadHistory` linked to inserted records with actor and timestamp; `items.upload_id` FK
- [x] Ingestion service implemented at `src/cost_query_pro/services/ingestion.py`
- [!] **Known gap — footer-based project number:** `project_number` is currently expected as a named column header in CSV/Excel files. Source documents where `project_number` appears only in a footer row or footer cell (rather than as a data column) are not handled. Ingestion of those files will fail with `INGEST_MISSING_COLUMNS`. Resolution deferred to Phase 2.

**Phase 1 exit criteria:**

- [x] Users can authenticate and query cost records via API *(done)*
- [x] At least one full ingest flow (CSV or Excel) runs end-to-end
- [x] Core schema stable and migration process repeatable *(done)*
- [x] CI passes: lint · security scan · migrations · unit tests

---

## Phase 2 — AI Agent Search + Operational Readiness

**Delivers:** The primary product feature — a natural language AI agent that answers infrastructure cost questions with cited project records. Also completes admin operations, ingestion reliability, and search performance tuning so the platform is dependable for daily internal use.

Example interaction:
> **User:** "What is the cost for a large diameter Jack and Bore?"
> **Agent:** "Large diameter (24" or more) Jack and Bore averages $XX/LF. Source records: [Project Name · Number · File · Year · Unit Cost]"

### AI Agent Search

**Provider strategy:** Claude (Anthropic) is the primary LLM. OpenAI is the backup provider. A provider abstraction layer allows transparent failover without changing the agent's tool definitions or response format.

#### Provider and Infrastructure

- [x] LLM provider abstraction layer implemented (`src/cost_query_pro/services/llm_provider.py`)
  - [x] Claude (claude-sonnet-4-6 or latest) as primary provider via `anthropic` SDK
  - [x] OpenAI (gpt-4o or latest) as backup provider via `openai` SDK
  - [x] Configurable provider selection via `settings.LLM_PROVIDER` (default: `claude`)
  - [x] Automatic fallback to OpenAI when Claude returns a non-retryable error
  - [x] Fallback events logged with provider, error type, and request ID
- [x] API keys for both providers stored in environment/secrets; missing key raises a clear startup warning, not a runtime crash
- [x] Provider selection and fallback behavior documented in `docs/`

#### Secure Query Pipeline

*The AI interprets user intent and narrates results. The backend performs all database access, query generation, and analytics. No raw project data is transmitted to external AI providers. See `docs/03_api/01_secure_ai_query_architecture.md` for the full specification.*

- [x] **Step 1 — Intent parsing call:** user question is sent to the LLM with no database access and no project data exposed
- [x] Structured search parameter payload schema defined and validated:
  - Required fields: `intent`, `item` (description keyword), `state`, `year_start`, `year_end`
  - Optional fields: `unit`, `price_min`, `price_max`
  - LLM does NOT generate SQL — it only extracts search criteria from the user's question
- [x] **Step 2 — Backend search:** FastAPI validates the structured payload and constructs all queries internally; LLM has no direct database access and never communicates with PostgreSQL
- [x] **Step 3 — Analytics layer:** backend computes summary statistics before any data leaves the infrastructure:
  - Core: `record_count`, `median_price`, `average_price`, `minimum_price`, `maximum_price`
  - Extended (as needed): percentiles, trend analysis, inflation adjustments, regional comparisons, outlier detection
- [x] **Step 4 — Data sanitization:** only aggregated summary statistics are transmitted to the LLM for response generation; the following are never included in LLM payloads:
  - Project names and project numbers
  - Contractor names
  - Bid tabulations
  - Uploaded source file contents
  - Internal notes
  - Raw database records
- [x] **Step 5 — Response generation call:** LLM receives only the sanitized aggregate summary and generates a natural-language answer
- [x] Security boundary verified by test: confirmed absence of raw project data (names, numbers, contractors) in all outbound LLM payloads
- [ ] [>] Enterprise mode (template-based response) — eliminates the second LLM call for deployments where no project-derived data may leave the environment — deferred to Phase 3

#### Agent Architecture and Tools

- [x] Agent architecture defined: two-call pipeline (intent parsing → response generation) with backend-controlled search and analytics between calls
- [x] Tool definitions implemented and versioned (tools return aggregated statistics, not raw project records):
  - [x] `keyword_search` — search items by description keyword; returns aggregate price stats and record count
  - [x] `filter_search` — filter by state, year range, unit type, and price range; returns aggregate stats
  - [x] `price_stats` — retrieve `record_count`, min/median/mean/max price for a given item description
  - [x] `project_lookup` — retrieve project-level summary metadata (count, year range, states covered); not individual project records
- [x] Tool schemas validated against the `anthropic` and `openai` function-calling specifications
- [x] Domain context system prompt covers: infrastructure vocabulary, pipe types, installation methods, size conventions (diameter ranges for "large", "small", etc.), unit abbreviations; AI role defined as translator and narrator — not a database operator
- [x] Prompt version tracked and stored alongside model version in config or DB

#### Endpoint and Response Contract

- [x] `POST /api/v1/agent/query` endpoint implemented
  - Request: `{ "question": "<natural language question>", "request_id": "<optional>" }`
  - Response: `{ "answer": "...", "record_count": N, "search_scope": {...}, "provider": "claude|openai", "model": "...", "request_id": "..." }`
- [x] Citation format enforced: search scope (item, state, year range, record count) included in every response; individual project records are excluded per the security architecture
- [x] Agent gracefully handles queries with no matching data (returns "no records found" message, not an error)
- [x] Agent gracefully handles ambiguous queries by asking a clarifying question rather than guessing
- [ ] [>] Streaming response support for the agent endpoint (Server-Sent Events or chunked transfer) — deferred to Phase 3; see *Agent Endpoint Response Delivery*
- [x] Agent endpoint requires JWT authentication

#### Cost Control and Rate Limiting

**Sequencing:** token usage logging is built first and the other items depend on it. State lives in Postgres, not Redis — the budget ledger must be durable, `redis` is declared in `pyproject.toml` but unused with no compose file, no Dockerfile, and no Redis service in CI (containerization is a Phase 3 item). One `llm_usage` table therefore serves three of the four items: the rows are the token log, the per-user/global rate limit is an indexed `COUNT` over a time window, and the spend cap is a `SUM(cost_usd)` for the calendar month.

- [x] **Step 1 — Token usage logged per request: provider, model, input tokens, output tokens, cost estimate.** Foundation for steps 2 and 3, and the only item that produces data — the budget figure in step 3 cannot be chosen sensibly until real usage has been recorded. Delivered:
  - `LLMProvider.complete()` now returns a `CompletionResult` (text, provider, model, input/output tokens) instead of a bare `str`, so `response.usage` is no longer discarded. `MeteredProvider` wraps the configured provider and accumulates one entry per completion; `get_llm_provider` returns it, which is safe because a fresh provider is built per request.
  - `llm_usage` table (migration `c7a4e2b91d38`): one row per completion, not per request — a query makes two calls, and a failover can split them across providers. Composite `(user_id, created_at)` and `(created_at)` indexes are in place to serve the step 2/3 COUNT and SUM queries.
  - `config/pricing.py` holds operator-maintained USD-per-MTok rates. An unpriced model records its token counts with a **NULL** `cost_usd` and logs once, so "unknown price" stays distinguishable from "free" when spend is summed.
  - Usage is recorded on every exit path including both graceful-degradation returns — an ambiguous question or an empty result set still spends tokens. `record_usage` never raises: accounting must not turn a successful answer into a failed request.
  - Fixed a pre-existing defect: `_resolve_model()` reported `claude_model` whenever `provider.name != "openai"`, so a fallback request served by OpenAI was attributed to Anthropic. Replaced with `_observed_provider`/`_observed_model`, which read what actually served the call.
  - 165 tests pass; migration verified in both directions.
- [ ] **Step 2 — Rate limiting on agent endpoint to control LLM API costs (per-user and global limits).** Additive once step 1 lands: a `COUNT` over `llm_usage` in a FastAPI dependency.
- [ ] **Step 3 — Monthly LLM spend cap configurable via `settings.LLM_MONTHLY_BUDGET_USD`; requests rejected gracefully when cap is reached.** Additive: a `SUM(cost_usd)` in the same dependency.
  - Steps 2 and 3 must be enforced in a route dependency, **not** inside `complete()`: `services/intent_parser.py:89` catches bare `Exception` and relabels it `INTENT_PARSE_ERROR`, which `api/agent.py:86` converts to a `200` clarifying question — a cap error raised inside the pipeline would be silently swallowed.
- [ ] [>] **Step 4 — Query result caching for identical or near-identical questions (configurable TTL)** — deferred. Cached cost answers go stale the moment new bid data lands, and the invalidation trigger is the ingestion pipeline, which is not yet implemented (see *Ingestion Reliability*). Revisit once ingestion can emit an invalidation signal.

#### Testing and Documentation

- [ ] Unit tests: provider abstraction (mock Claude, mock OpenAI), tool dispatch, citation format, fallback logic
- [ ] Unit tests: data sanitization layer — assert raw project records are excluded from all LLM payloads
- [ ] Unit tests: analytics layer — verify aggregate stats computed correctly before LLM response call
- [ ] Integration test: end-to-end natural language query → intent parsing → backend search → aggregated response (Claude)
- [ ] Integration test: end-to-end natural language query → intent parsing → backend search → aggregated response (OpenAI fallback)
- [ ] Security model documented in `docs/`: LLM responsibilities vs. backend responsibilities; enumerated list of data excluded from LLM payloads

### Authentication Enhancements

- [ ] **[P2-C-2] — CRITICAL, do first.** Remove the hardcoded JWT signing-key default and require a strong secret. `Settings.secret_key` currently defaults to the literal `"default_secret_key"` (18 bytes) and `Settings.environment` defaults to `"production"`, so a deployment that does not set `SECRET_KEY` signs tokens with a value published in this repository — anyone reading the repo can forge an `is_admin` token and reach the irreversible purge endpoint. There is no length validation either; the current key trips PyJWT's `InsecureKeyLengthWarning` (below the 32-byte RFC 7518 minimum for HS256).
  - Change to `secret_key: str = Field(..., min_length=32)` so a missing or short secret aborts startup instead of falling back
  - Default `environment` to `development` so an unconfigured deployment fails safe
  - Add a test asserting startup fails with no `SECRET_KEY` set
  - See `docs/09_audit_reports/02_phase_2/20260727_mypy_remediation_audit_report.md`
- [ ] Replace the tautological `test_revoked_user_rejected` in `tests/unit_tests/test_auth_jwt.py` with an endpoint-level assertion. It sets `user.is_admin = False`, then hardcodes `if not user.is_admin: access_granted = False`, then asserts `not access_granted` — always true regardless of application behaviour. Carried from the 2026-06-24 test-file audit (CRITICAL) and re-verified 2026-07-27; pairs with the token-revocation work below
- [ ] `roles` and `permissions` tables migrated; `role_permissions` bridge table added (carried from Phase 1)
- [ ] Seed baseline roles (`admin`, `user`) and permission matrix defined and applied
- [ ] All `is_admin` boolean checks replaced with role-based permission lookup
- [ ] Role assignment and revocation endpoints implemented and admin-authorized

### Admin Operations and Data Governance

- [x] Data purge by year cutoff with cascade (admin authorized)
- [!] **[P2-C-1]** Purged data archived to `archived_projects` and `archived_items` — **not implemented; was previously marked done in error.** `api/purge.py` deletes items and projects outright and never writes an archive row. The `ArchivedProject` / `ArchivedItem` models are not imported in `models/__init__.py`, are absent from `Base.metadata`, and have no migration, so the destination tables do not exist. **Admin purge is therefore irreversible today**, contrary to what this line claimed. Blocked on **[C-2]** below (the models must be fixed and migrated before purge can write to them). Once unblocked:
  - Write archive rows inside the same transaction as the delete, so a failed archive aborts the purge
  - Record `purged_by_user_id` and the archive timestamp
  - Cover with a test asserting that purged rows are recoverable from the archive tables
- [x] User management: list · delete · promote to admin
- [ ] Audit log retrieval endpoint for admin review
- [ ] Duplicate detection rules and conflict handling on ingest
- [ ] Immutable audit event schema for: auth · ingest · data-modify · purge · role-change
- [ ] Retention policy defined by data type and environment
- [ ] Admin how-to guide for user and data lifecycle tasks
- [ ] All destructive actions require explicit authorization and are fully auditable
- [ ] Admin operations have endpoint-level integration tests

### Schema Continuations (carried from Phase 1)

- [ ] `users.email` column added; unique constraint migrated
- [ ] `roles`, `permissions`, `role_permissions` tables migrated (see Authentication Enhancements above)
- [ ] FK naming convention applied consistently across all tables; referential actions (`RESTRICT`/`CASCADE`/`SET NULL`) documented per table
- [x] Fix model bugs and write migrations for `upload_history`, `data_quality_issues` (done in Phase 1)
- [ ] Fix model bugs and write migrations for `system_settings` (correct FK references, verify column types)
- [ ] **[C-2]** Fix model bugs and write migrations for `archived_projects`, `archived_items`:
  - Rename `ArchivedProject.__tablename__` from `"projects"` → `"archived_projects"`
  - Rename `ArchivedItem.__tablename__` from `"items"` → `"archived_items"`
  - Fix `ArchivedProject.archived_at` column type: `Boolean` → `DateTime` (with `nullable=False`)
  - Add missing `upload_id` FK column to `ArchivedItem` (mirrors `Item.upload_id`)
  - Correct `ArchivedItem.project_id` FK reference from `projects.id` → `archived_projects.id`
  - Register both models in `models/__init__.py` so they reach `Base.metadata` (they are currently invisible to Alembic autogenerate, which is why migration `c7a4e2b91d38` had to be hand-written)
  - Write and test migration; verify both `upgrade` and `downgrade` paths
  - **Blocks [P2-C-1]** (purge-to-archive) under *Admin Operations and Data Governance* — until this lands, admin purge is irreversible
  - Note: until the tablename collisions are fixed, importing `ArchivedProject` alongside `Project` raises `InvalidRequestError`; both currently declare `__tablename__ = "projects"` / `"items"`
- [ ] Updated ERD published after all Phase 2 schema changes land

### Ingestion Reliability

- [x] `UploadHistory` model tracks upload status
- [ ] Ingestion job state machine: queued · running · succeeded · failed
- [ ] Downloadable error report per ingestion run
- [ ] Retry logic for transient parser/database failures
- [ ] Import template with field mapping documentation (must document both column-header and footer placement conventions for `project_number`)
- [ ] Re-uploading the same file does not create uncontrolled duplicates
- [ ] PDF ingestion via pdfplumber: parse bid tabulation tables from PDF uploads and extract `project_number` from page-level footer/header metadata when it is not present in table columns

#### Footer-Based Project Number Extraction (resolves Phase 1 known gap)

Source documents — particularly Excel and PDF bid tabulation exports — commonly place the project number in a footer row at the bottom of the sheet rather than as a dedicated data column. The ingestion service must handle both placements.

- [ ] Define footer detection heuristics: inspect trailing rows below the last data row for cells that match the project-number pattern (alphanumeric code, typically `[A-Z0-9\-]+`); configurable scan depth (default: last 5 rows)
- [ ] Ingestion service updated: if `project_number` column is absent from headers, attempt footer scan before raising `INGEST_MISSING_COLUMNS`; log which extraction path was used per upload
- [ ] Footer-extracted `project_number` validated against the same rules as header-sourced values (non-empty, pattern match, length limits)
- [ ] Ambiguity guard: if footer scan finds more than one candidate `project_number` value, reject the file with a clear error (`INGEST_AMBIGUOUS_PROJECT_NUMBER`) and list the candidates in the error detail
- [ ] Tests: upload CSV with `project_number` in footer row — assert correct extraction and insertion
- [ ] Tests: upload Excel with `project_number` in footer cell — assert correct extraction and insertion
- [ ] Tests: upload file with `project_number` absent from both header and footer — assert `INGEST_MISSING_COLUMNS` error
- [ ] Tests: upload file with multiple conflicting project numbers in footer — assert `INGEST_AMBIGUOUS_PROJECT_NUMBER` error
- [ ] Import template and API documentation updated to describe supported placement conventions (column header vs. footer row) and expected format for each

### Search Performance

- [ ] Index plan reviewed and indexes added: `items(project_id)` · `items(unit)` · `projects(year)` · `projects(state)`
- [ ] Trigram or full-text index evaluated for `item_description` keyword search
- [ ] EXPLAIN plan reviewed for top 5 search query patterns
- [ ] Query timeout and defensive pagination limits enforced
- [ ] Caching evaluated for high-frequency lookups (distinct units, price ranges)
- [ ] P95 search latency target documented and validated under expected data volume

**Phase 2 exit criteria:**

- [ ] AI agent answers natural language cost questions with cited source records using Claude; OpenAI fallback verified
- [ ] Admin workflows complete: user lifecycle · purge · audit log retrieval
- [ ] Ingestion failures are diagnosable by operators without reading server internals
- [ ] P95 search latency target met

---

## Phase 3 — Production Platform

**Delivers:** The platform is deployable, monitorable, and secure for broader rollout. Includes containerization, a hardened CI/CD pipeline, structured observability, and a validated backup/recovery process.

### Deployment and CI/CD

- [x] CI quality gate: pre-commit (lint/format), bandit (SAST), pip-audit (dependencies)
- [x] CI type gate: `mypy --strict src/cost_query_pro` in the Quality job of both workflows; strictness configured in `[tool.mypy]` so local runs match CI
- [ ] Raise `tests/` to strict typing and drop the `[[tool.mypy.overrides]]` relaxation in `pyproject.toml` — roughly 230 findings, almost all missing annotations on test functions; the application-code gate is already enforced and does not depend on this
- [ ] Add `alembic check` to the CI test gate so model/migration drift fails the build rather than surfacing in someone's next autogenerate (drift found and fixed once already in `a3f5c81e7b24`)
- [ ] **[P2-M-2]** Make coverage measurable. `pytest-cov` is declared only in `[project.optional-dependencies].dev`, which `uv sync --dev` does not install (uv reads `[dependency-groups].dev`), so `--cov` errors out and the `[coverage:run]` / `[coverage:report]` config in `setup.cfg` is unreachable. Move the dependency, then decide whether coverage reports or gates
- [ ] **[P2-M-3]** Migrate the test client to `httpx2`. Starlette 1.x warns that using `httpx` with `starlette.testclient` is deprecated; the whole suite runs through `fastapi.testclient.TestClient`, so this becomes a break in a future release. The previous Starlette major upgrade silently broke an uncovered route (see `20260727_mypy_remediation_audit_report.md`, D-1) — schedule this rather than absorb it unplanned
- [x] CI test gate: PostgreSQL service, Alembic migration, pytest
- [ ] Dockerfile and docker-compose with production-safe defaults
- [ ] Environment promotion model: dev → staging → prod
- [ ] Migration step in deployment pipeline with rollback guardrails
- [ ] Release versioning and documented rollback procedure
- [ ] One-command deployment repeatable from a clean environment

### Security Hardening

- [x] Dependency vulnerability scanning (pip-audit in CI)
- [x] Static security analysis (bandit in CI)
- [ ] TLS enforced on all external-facing traffic
- [ ] Login throttling and lockout after repeated failures (carried from Phase 1)
- [ ] API rate limiting on auth and agent endpoints
- [ ] Input sanitization hardened at parser and API boundaries
- [ ] Secrets moved to managed secret storage (not `.env` in production) — note **[P2-C-2]** under *Authentication Enhancements* must land first; it is a live auth-bypass risk, not a Phase 3 hardening task
- [ ] JWT refresh token flow and token revocation implemented (carried from Phase 1)
- [ ] Least-privilege role/permission review completed and signed off
- [ ] [>] Enterprise AI mode: template-based response path that eliminates the second LLM call — only the user's question leaves the environment; no database-derived data transmitted to external providers (carried from Phase 2) — unblocks streaming; see *Agent Endpoint Response Delivery*

### Observability and Reliability

- [ ] Structured logging standardized across all modules
- [ ] Metrics captured: auth events · ingestion runs · query latency · agent calls · LLM token usage · error rates
- [ ] Error tracking and alert routing configured
- [ ] SLOs and SLIs defined for availability and performance
- [ ] Backup policy implemented and restoration drill completed
- [ ] Operator runbook: failure modes, remediation steps, escalation path

### Performance Validation

- [ ] Expected workload profile defined: users · queries/min · upload sizes · agent calls/day
- [ ] Load and soak tests run in staging
- [ ] DB connection pooling and app workers tuned
- [ ] Scaling triggers and actions documented

### Agent Endpoint Response Delivery (deferred from Phase 2)

`POST /api/v1/agent/query` is blocking: the caller waits through two LLM round trips and a database query before receiving a single JSON payload. Streaming was deferred out of Phase 2 rather than dropped — the preconditions below must hold first, because today there is no client that can consume a stream and the response path itself is not settled.

**Preconditions (all must be true before starting):**

- [ ] An interactive client exists that can render incremental output (the current `web/views/routes.py` dashboard is server-rendered Jinja and does not call the agent endpoint)
- [ ] Enterprise AI mode is resolved (see *Security Hardening*) — that item eliminates the second LLM call, which is the only streamable portion of the pipeline
- [ ] Cost control is implemented on the blocking endpoint first (rate limiting, per-request token logging, spend cap) so streaming inherits the instrumentation rather than duplicating it

**Implementation scope, in order:**

- [ ] **Stage 1 — status events only.** SSE endpoint emitting pipeline progress (`parsing` → `searching` → `found N records`) with the final answer delivered as one event. Captures most of the perceived-latency win; all metadata is emitted before any LLM text, so the provider-fallback and token-accounting problems below do not arise.
- [ ] **Stage 2 — token streaming.** Add `stream()` to the `LLMProvider` protocol and implement on `ClaudeProvider`, `OpenAIProvider`, and `FallbackLLMProvider`
- [ ] Fallback semantics defined for mid-stream provider failure (partial output has already reached the client and cannot be retracted)
- [ ] Token usage recorded correctly when a client disconnects mid-stream (tokens are billed regardless; usage totals arrive at end-of-stream)
- [ ] Mid-stream errors surfaced as a typed `error` event — status and headers are committed with the first chunk, so `AppError` can no longer become an HTTP status code
- [ ] Response contract documented by hand: `StreamingResponse` bypasses `response_model` validation and OpenAPI schema generation
- [ ] Reverse-proxy buffering disabled for this route (`proxy_buffering off` / `X-Accel-Buffering: no`), otherwise the response is re-buffered and streaming has no effect
- [ ] Blocking `POST /api/v1/agent/query` retained alongside the streaming route so scripted and API consumers keep the stable JSON contract

**Phase 3 exit criteria:**

- [ ] Repeatable deployment pipeline with documented rollback
- [ ] SLOs defined and observable
- [ ] Backup restore tested successfully

---

## Phase 4 — Intelligence Layer

**Delivers:** The platform evolves from historical lookup to decision-support intelligence, with cost trend analysis, comparative benchmarks, export/reporting, and an initial predictive capability.

### Analytics Foundation

- [ ] Cost metric catalog defined: mean · median · percentile · volatility
- [ ] Inflation-adjusted cost normalization implemented
- [ ] Regional and temporal benchmark views
- [ ] Confidence indicators on derived metrics
- [ ] Analytics results reproducible and traceable to source records

### Visualization and Reporting

- [ ] Trend charts by item, location, and period
- [ ] Comparative views: region vs region · year vs year
- [ ] Export support for reports (CSV and PDF)
- [ ] Saved query/report definitions
- [ ] Core stakeholders can answer top 10 estimation questions without writing SQL

### Predictive Capabilities

- [ ] Target prediction use cases defined and baseline heuristics documented
- [ ] Train / validate / evaluate pipeline implemented
- [ ] Feature lineage and model version metadata tracked
- [ ] Model quality monitoring and retraining triggers
- [ ] Explainability notes published for each prediction output
- [ ] Model outperforms baseline heuristics by agreed threshold

**Phase 4 exit criteria:**

- [ ] Trend, benchmark, and regional insights available
- [ ] Initial predictive capability validated
- [ ] All analytics outputs explainable and traceable to source records

---

## Reference

### Suggested Milestones

| Milestone | Target | Scope |
|-----------|--------|-------|
| M1 | Weeks 1–4 | Phase 1 core complete (auth, schema, API) — *largely done; ingestion + RBAC remaining* |
| M2 | Weeks 5–8 | Phase 1 ingestion complete; MVP gate passed |
| M3 | Weeks 9–14 | Phase 2 complete: AI agent + admin + ingestion reliability |
| M4 | Weeks 15–20 | Phase 3 complete: deployment, security, observability |
| M5 | Weeks 21+ | Phase 4: analytics and predictive pilot |

### Risks

| Risk | Mitigation |
|------|-----------|
| Heterogeneous source formats break ingestion | Strict templates + per-row error isolation + parser fallbacks |
| Project number in document footer not recognized | Footer-row scan with configurable depth; ambiguity guard rejects files with conflicting candidates; template docs clarify supported placement conventions |
| AI agent returns uncited or hallucinated cost figures | Agent always queries live DB; every answer cites specific record IDs and source files |
| Claude API unavailable or degraded | Automatic fallback to OpenAI; fallback events logged and alerted |
| LLM API costs exceed budget at scale | Rate limiting on agent endpoint + query caching + token usage monitoring + monthly spend cap |
| Query latency grows with data volume | Index strategy + query profiling + hot-path caching |
| Auth/role regression exposes sensitive data | Authorization test matrix + periodic permission audits |
| Migration drift across environments | CI migration checks + environment parity + rollback drills |
| Schema inconsistency causes rework | ERD signoff milestone + migration freeze window before each phase |

### Success Metrics

| Metric | Target |
|--------|--------|
| Ingestion success rate (file-level) | >= 95% after template compliance |
| P95 structured search latency | < 700 ms |
| AI agent response time | < 5 s for typical cost queries (Claude primary) |
| AI agent fallback activation rate | < 5% of requests trigger OpenAI fallback |
| AI agent citation accuracy | 100% of answers include traceable project record references |
| Time-to-answer for common estimation questions | 50% reduction vs manual lookup |
| Sensitive action audit coverage | 100% logged with actor + timestamp |
