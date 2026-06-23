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
- [>] PDF table extraction via pdfplumber — deferred to Phase 2
- [x] Idempotency: composite key `(project_number, item_description, unit)` — duplicates skipped
- [x] Ingestion lineage stored: `UploadHistory` linked to inserted records with actor and timestamp; `items.upload_id` FK
- [x] Ingestion service implemented at `src/cost_query_pro/services/ingestion.py`

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

- [ ] `POST /api/v1/agent/query` endpoint implemented
  - Request: `{ "query": "<natural language question>" }`
  - Response: `{ "answer": "...", "citations": [...], "provider": "claude|openai", "model": "..." }`
- [ ] Citation format enforced: every answer includes project name, number, source file, year, and unit cost
- [ ] Agent gracefully handles queries with no matching data (returns "no records found" message, not an error)
- [ ] Agent gracefully handles ambiguous queries by asking a clarifying question rather than guessing
- [ ] Streaming response support for the agent endpoint (Server-Sent Events or chunked transfer)
- [ ] Agent endpoint requires JWT authentication

#### Cost Control and Rate Limiting

- [ ] Rate limiting on agent endpoint to control LLM API costs (per-user and global limits)
- [ ] Token usage logged per request: provider, model, input tokens, output tokens, cost estimate
- [ ] Monthly LLM spend cap configurable via `settings.LLM_MONTHLY_BUDGET_USD`; requests rejected gracefully when cap is reached
- [ ] Query result caching for identical or near-identical questions (configurable TTL)

#### Testing and Documentation

- [ ] Unit tests: provider abstraction (mock Claude, mock OpenAI), tool dispatch, citation format, fallback logic
- [ ] Unit tests: data sanitization layer — assert raw project records are excluded from all LLM payloads
- [ ] Unit tests: analytics layer — verify aggregate stats computed correctly before LLM response call
- [ ] Integration test: end-to-end natural language query → intent parsing → backend search → aggregated response (Claude)
- [ ] Integration test: end-to-end natural language query → intent parsing → backend search → aggregated response (OpenAI fallback)
- [ ] Security model documented in `docs/`: LLM responsibilities vs. backend responsibilities; enumerated list of data excluded from LLM payloads

### Authentication Enhancements

- [ ] `roles` and `permissions` tables migrated; `role_permissions` bridge table added (carried from Phase 1)
- [ ] Seed baseline roles (`admin`, `user`) and permission matrix defined and applied
- [ ] All `is_admin` boolean checks replaced with role-based permission lookup
- [ ] Role assignment and revocation endpoints implemented and admin-authorized

### Admin Operations and Data Governance

- [x] Data purge by year cutoff with cascade (admin authorized)
- [x] Purged data archived to `archived_projects` and `archived_items`
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
  - Write and test migration; verify both `upgrade` and `downgrade` paths
- [ ] Updated ERD published after all Phase 2 schema changes land

### Ingestion Reliability

- [x] `UploadHistory` model tracks upload status
- [ ] Ingestion job state machine: queued · running · succeeded · failed
- [ ] Downloadable error report per ingestion run
- [ ] Retry logic for transient parser/database failures
- [ ] Import template with field mapping documentation
- [ ] Re-uploading the same file does not create uncontrolled duplicates

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
- [ ] Secrets moved to managed secret storage (not `.env` in production)
- [ ] JWT refresh token flow and token revocation implemented (carried from Phase 1)
- [ ] Least-privilege role/permission review completed and signed off
- [ ] [>] Enterprise AI mode: template-based response path that eliminates the second LLM call — only the user's question leaves the environment; no database-derived data transmitted to external providers (carried from Phase 2)

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
