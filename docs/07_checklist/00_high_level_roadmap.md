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

- [x] Core entities in place: `users`, `projects`, `items`, `audit_logs`, `upload_history`, `data_quality_issues`, `archived_projects`, `archived_items`, `system_settings`
- [x] Three ordered migrations: initial schema → quantity column → audit logs
- [x] `alembic upgrade head` runs in CI as a smoke test
- [x] Fresh database reproducible from migrations with no manual steps
- [ ] `users.email` column and unique constraint (username unique exists; email not yet added)
- [ ] `roles` and `permissions` tables with unique name constraints
- [ ] Check constraints for non-negative numeric fields (`unit_price`, `quantity`)
- [ ] FK naming consistent across all tables; referential actions (`RESTRICT`/`CASCADE`/`SET NULL`) documented
- [ ] Downgrade path validated for all migrations
- [ ] Canonical ERD published in `docs/` (tables, PK/FK, cardinality, delete behavior)

### Core API

- [x] Project endpoints: create, read, update, delete, list (state/year filter), items-by-project
- [x] Item endpoints: create, read, update, delete, search (8 filter types), distinct units, price-range stats
- [x] Admin endpoints: list users, delete user, promote user, purge data by year cutoff
- [x] Pydantic request/response validation on all public endpoints
- [x] Pagination on all list/search routes (skip/limit, max 500)
- [x] Health check at `/` (returns DB connectivity status)
- [ ] Deterministic sort order on all paginated responses
- [ ] Structured API-level error codes for client troubleshooting
- [ ] Duplicate `/search` route definition in `items.py` removed/consolidated
- [ ] OpenAPI docs verified accurate for all implemented behavior

### Ingestion Pipeline (CSV / Excel / PDF)

*Dependencies installed (pandas, pdfplumber, pdfminer-six). Supporting models (`UploadHistory`, `DataQualityIssue`) in place. Endpoints and service not yet implemented.*

- [ ] File upload endpoint: `POST /api/v1/ingest/upload`
- [ ] Canonical import schema defined (required/optional columns, expected headers)
- [ ] File-level validation: type, size, required header presence
- [ ] Row-level validation: numeric fields, unit values, date ranges
- [ ] Unit and text field normalization before persistence
- [ ] Structured ingest report per run: inserted · skipped · failed · warnings
- [ ] PDF table extraction via pdfplumber with fallback for non-tabular layouts
- [ ] Idempotency: re-ingesting equivalent rows does not create duplicates
- [ ] Ingestion lineage stored: `UploadHistory` linked to inserted records with actor and timestamp
- [ ] Ingestion service implemented at `src/cost_query_pro/services/ingestion.py`

**Phase 1 exit criteria:**

- [ ] Users can authenticate and query cost records via API *(done)*
- [ ] At least one full ingest flow (CSV or Excel) runs end-to-end
- [ ] Core schema stable and migration process repeatable *(done)*
- [ ] CI passes: lint · security scan · migrations · unit tests

---

## Phase 2 — AI Agent Search + Operational Readiness

**Delivers:** The primary product feature — a natural language AI agent that answers infrastructure cost questions with cited project records. Also completes admin operations, ingestion reliability, and search performance tuning so the platform is dependable for daily internal use.

Example interaction:
> **User:** "What is the cost for a large diameter Jack and Bore?"
> **Agent:** "Large diameter (24" or more) Jack and Bore averages $XX/LF. Source records: [Project Name · Number · File · Year · Unit Cost]"

### AI Agent Search

**Provider strategy:** Claude (Anthropic) is the primary LLM. OpenAI is the backup provider. A provider abstraction layer allows transparent failover without changing the agent's tool definitions or response format.

#### Provider and Infrastructure

- [ ] LLM provider abstraction layer implemented (`src/cost_query_pro/services/llm_provider.py`)
  - [ ] Claude (claude-sonnet-4-6 or latest) as primary provider via `anthropic` SDK
  - [ ] OpenAI (gpt-4o or latest) as backup provider via `openai` SDK
  - [ ] Configurable provider selection via `settings.LLM_PROVIDER` (default: `claude`)
  - [ ] Automatic fallback to OpenAI when Claude returns a non-retryable error
  - [ ] Fallback events logged with provider, error type, and request ID
- [ ] API keys for both providers stored in environment/secrets; missing key raises a clear startup warning, not a runtime crash
- [ ] Provider selection and fallback behavior documented in `docs/`

#### Agent Architecture and Tools

- [ ] Agent architecture defined: tool-use model calling internal search endpoints
- [ ] Tool definitions implemented and versioned:
  - [ ] `keyword_search` — search items by description keyword with optional filters
  - [ ] `filter_search` — search by state, year range, unit type, and price range
  - [ ] `price_stats` — retrieve min/max/average price for a given item description
  - [ ] `project_lookup` — retrieve project metadata by name, number, or state
- [ ] Tool schemas validated against the `anthropic` and `openai` function-calling specifications
- [ ] Domain context system prompt covers: infrastructure vocabulary, pipe types, installation methods, size conventions (diameter ranges for "large", "small", etc.), unit abbreviations
- [ ] Prompt version tracked and stored alongside model version in config or DB

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
- [ ] Integration test: end-to-end natural language query → tool calls → cited records (Claude)
- [ ] Integration test: end-to-end natural language query → tool calls → cited records (OpenAI fallback)
- [ ] Agent prompt, tool schema, provider config, and response format documented in `docs/`

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
