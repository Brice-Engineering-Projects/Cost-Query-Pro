# Cost Query Pro - Detailed Roadmap Checklist

## 1. Product Direction

Cost Query Pro is an infrastructure cost intelligence platform for engineers, estimators, and analysts. It centralizes historical bid tabulation data from spreadsheets, CSVs, and PDFs, then exposes clean, searchable cost history through APIs and internal workflows.

Primary product outcomes:

- Faster estimate generation from historical unit cost evidence.
- Better bid defensibility via traceable cost history and metadata.
- Lower manual effort for ingestion, cleanup, and retrieval.
- Controlled access to sensitive project and pricing data.

Core technical direction:

- Backend: FastAPI
- Data layer: PostgreSQL + SQLAlchemy + Alembic
- Ingestion/transformation: pandas + parser services
- Access/security: JWT auth + role-aware admin controls

## 2. Delivery Model

## 2.1 Planning Assumptions

- Roadmap horizon: 6 to 12 months.
- Execution cadence: 2-week sprints.
- Delivery style: phase-based with release gates.
- Team model: 1 to 3 backend engineers, 1 data engineer part-time, 1 product owner.

## 2.2 Global Definition of Done

A work item is complete only when all items below are true:

- [ ] Code implemented and peer reviewed.
- [ ] Unit and integration tests added or updated.
- [ ] Migrations applied and rollback path validated.
- [ ] API contract documented.
- [ ] Logging and error handling in place.
- [ ] Security and authorization checks verified.
- [ ] Documentation updated in `docs/`.

## 2.3 Release Gates (All Phases)

- [ ] Functional gate: target user workflows pass end-to-end tests.
- [ ] Reliability gate: no P1/P2 open defects.
- [ ] Security gate: authentication/authorization reviewed.
- [ ] Data quality gate: ingestion validation thresholds met.
- [ ] Ops gate: logs, health checks, and recovery procedures documented.

## 3. Phase Overview

## 3.1 Phase 1 - Foundation MVP

Objective: deliver a secure, queryable historical cost system with baseline ingestion.

Exit criteria:

- [ ] Users can authenticate and query cost records.
- [ ] At least one full ingest flow (CSV/Excel) runs in production-like environment.
- [ ] Core schema is stable and migration process repeatable.

## 3.2 Phase 2 - Operational Internal Tool

Objective: make the platform reliable for regular internal use and administration.

Exit criteria:

- [ ] Admin workflows are complete (user lifecycle, purge, audit).
- [ ] Ingestion errors are diagnosable with logs and reports.
- [ ] Query performance is acceptable for expected internal load.

## 3.3 Phase 3 - Production Platform

Objective: harden for broader rollout with observability, security, and deployment maturity.

Exit criteria:

- [ ] Repeatable deployment pipeline and runbook.
- [ ] SLOs defined and observable.
- [ ] Backups and restoration tested.

## 3.4 Phase 4 - Intelligence Layer

Objective: evolve from historical lookup to decision-support intelligence.

Exit criteria:

- [ ] Trend, benchmark, and regional insights available.
- [ ] Initial predictive capability validated against baseline heuristics.
- [ ] Analytics outputs are explainable and traceable.

## 4. Detailed Checklist by Phase

## 4.1 Phase 1 - Foundation MVP

### 4.1.1 Architecture and Environment

- [ ] Confirm canonical project structure under `src/cost_query_pro/`.
- [ ] Finalize configuration strategy for local/test/prod settings.
- [ ] Validate DB connectivity strategy and session lifecycle management.
- [ ] Standardize error response format across API routes.
- [ ] Add application health endpoint (`/health` or equivalent).

Acceptance criteria:

- [ ] Local bootstrap is reproducible from clean environment.
- [ ] Application starts with clear startup diagnostics.

### 4.1.2 Data Model and Migrations

- [ ] Finalize minimum entities: users, projects, items, audit logs, ingestion jobs.
- [ ] Ensure foreign keys and indexes support target query paths.
- [ ] Review migration naming and ordering conventions.
- [ ] Add migration smoke test in CI.
- [ ] Validate downgrade strategy for latest migration set.
- [ ] Add uniqueness constraints for `users.username`, `users.email`, `roles.role_name`, and `permissions.permission_name`.
- [ ] Add schema-level check constraints for non-negative numeric fields (for example, `quantity`, `unit_price`, `construction_cost`).
- [ ] Resolve FK naming consistency between `bid_items.source_id` and `data_sources.data_source_id`.
- [ ] Define delete/update referential actions for all FKs (`RESTRICT`, `CASCADE`, or `SET NULL`) and document rationale.

Acceptance criteria:

- [ ] Fresh database can be created from migrations without manual edits.
- [ ] Schema supports item + project metadata retrieval in one query pattern.
- [ ] Naming and FK references are internally consistent across all tables.

### 4.1.3 Authentication and Authorization

- [ ] Harden password hashing settings and policy requirements.
- [ ] Finalize JWT expiration, refresh behavior, and token claims.
- [ ] Enforce protected route access with shared dependency layer.
- [ ] Add role checks for admin-only routes.
- [ ] Add lockout/throttling strategy for repeated failed logins.
- [ ] Add `role_permissions` bridge table to support true role-based permission assignment.
- [ ] Seed baseline roles/permissions and verify permission matrix for admin/user flows.

Acceptance criteria:

- [ ] Auth tests cover success, failure, expired token, invalid role.
- [ ] Unauthorized access is blocked consistently across endpoints.
- [ ] Every protected endpoint is mapped to explicit permissions, not only role names.

### 4.1.4 Core APIs

- [ ] Stabilize endpoint contracts for auth, projects, items, and admin.
- [ ] Add request/response schema validation for all public endpoints.
- [ ] Add pagination contract for list/search routes.
- [ ] Add deterministic sorting defaults for search results.
- [ ] Add API-level error codes for client troubleshooting.

Acceptance criteria:

- [ ] OpenAPI docs are accurate for implemented behavior.
- [ ] Contract tests pass for all MVP routes.

### 4.1.5 Ingestion Pipeline (CSV/Excel/PDF Baseline)

- [ ] Define canonical import schema (required/optional columns).
- [ ] Implement file-level validation (type, size, headers).
- [ ] Implement row-level validation (units, numeric fields, dates).
- [ ] Normalize units and text fields before persistence.
- [ ] Capture ingest report: inserted, skipped, failed, warnings.
- [ ] Add basic PDF table extraction fallback strategy.
- [ ] Implement canonical mapping from raw `item_description` to `cost_items.canonical_description`.
- [ ] Add deterministic lookup/creation rules for dimensions: `units`, `agencies`, `regions`, `project_types`, `project_size`, `pipe_use`.
- [ ] Store ingestion lineage from `bid_items` to `data_sources` and processing actor/timestamp.

Acceptance criteria:

- [ ] Ingest run generates structured summary and error details.
- [ ] Invalid rows are isolated without failing entire batch unless configured.
- [ ] Re-ingesting equivalent source rows resolves to the same canonical dimensions.

### 4.1.6 Query and Search

- [ ] Implement keyword item search.
- [ ] Add state/location filter support.
- [ ] Add year and date-range filters.
- [ ] Return project context in search response.
- [ ] Add optional min/max unit-price filters.
- [ ] Add combined filters for `project_type`, `pipe_use`, `material_type`, and `delivery_method`.
- [ ] Define and test search query path joining `bid_items -> projects -> agencies/regions -> cost_items`.
- [ ] Add explicit index plan for high-cardinality filters and join columns.

Acceptance criteria:

- [ ] Query response includes item, unit, unit price, project, location, year.
- [ ] Search behavior is stable across pagination boundaries.
- [ ] Query plan for top 5 search patterns uses intended indexes.

### 4.1.7 Testing and Quality (MVP)

- [ ] Extend unit tests for auth, route validation, and services.
- [ ] Add integration tests for ingest to query path.
- [ ] Add smoke tests for startup and health endpoint.
- [ ] Establish baseline coverage target (for example, >= 70%).

## 4.2 Phase 2 - Operational Internal Tool

### 4.2.1 Data Governance and Admin Operations

- [ ] Implement duplicate-detection rules and conflict handling.
- [ ] Build purge/archive workflows with confirmation safeguards.
- [ ] Expose audit log retrieval for admin actions.
- [ ] Add user management flows (create, disable, role update).
- [ ] Define retention policy by data type and environment.
- [ ] Define audit logging pattern for polymorphic `audit_logs.record_id` references.
- [ ] Add immutable audit event schema for auth, ingest, data-modify, purge, and role-change actions.

Acceptance criteria:

- [ ] All destructive actions require explicit authorization and are auditable.
- [ ] Admin operations have endpoint-level integration tests.
- [ ] Audit trail can reconstruct who changed what, when, and from which source file.

### 4.2.2 Ingestion Reliability and Operations

- [ ] Introduce ingestion job states (queued/running/succeeded/failed).
- [ ] Add idempotency mechanism for repeated uploads.
- [ ] Add import templates and validation hints.
- [ ] Produce downloadable error report per ingestion run.
- [ ] Add retry rules for transient parser/database failures.

Acceptance criteria:

- [ ] Operators can diagnose failed imports without reading server internals.
- [ ] Re-uploading same file does not create uncontrolled duplicates.

### 4.2.3 Search Performance and Usability

- [ ] Add and tune indexes for top filter combinations.
- [ ] Add explain-plan review for expensive queries.
- [ ] Enforce pagination limits and response size controls.
- [ ] Add query timeout and defensive safeguards.
- [ ] Evaluate caching for frequent lookups.
- [ ] Add targeted indexes for `bid_items(project_id)`, `bid_items(cost_item_id)`, `bid_items(contractor_id)`, `projects(bid_date)`, and `projects(region_id, project_type_id)`.
- [ ] Evaluate text search strategy for `item_description` and `canonical_description` (trigram or full-text).

Acceptance criteria:

- [ ] P95 search response time target documented and met in internal load test.
- [ ] Full join search remains within target under expected data volume.

### 4.2.4 Operational Documentation

- [ ] Create operator runbook for ingestion troubleshooting.
- [ ] Document known failure modes and remediation steps.
- [ ] Add admin how-to for user and data lifecycle tasks.

## 4.3 Phase 3 - Production Platform

### 4.3.1 Deployment and CI/CD

- [ ] Containerize service with production-safe defaults.
- [ ] Add build/test/lint pipeline gates.
- [ ] Add migration step in deployment workflow with guardrails.
- [ ] Add environment promotion model (dev -> staging -> prod).
- [ ] Add release versioning and rollback procedure.

Acceptance criteria:

- [ ] One-command or one-pipeline deployment is repeatable.
- [ ] Rollback can be executed using documented procedure.

### 4.3.2 Security Hardening

- [ ] Enforce TLS everywhere external traffic is served.
- [ ] Add API rate limiting and abuse controls.
- [ ] Harden input sanitization and parser boundaries.
- [ ] Move secrets to managed secret storage.
- [ ] Add dependency and image vulnerability scanning.
- [ ] Conduct role/permission review for least privilege.

Acceptance criteria:

- [ ] Security checklist signed off before production release.

### 4.3.3 Observability and Reliability

- [ ] Standardize structured logging across modules.
- [ ] Add metrics for auth, ingestion, query latency, and failures.
- [ ] Add error tracking and alert routing.
- [ ] Define SLOs/SLIs for availability and performance.
- [ ] Implement backup policy and restoration drill.

Acceptance criteria:

- [ ] On-call can identify and triage failures within defined response window.
- [ ] Backup restore tested successfully at least once per quarter.

### 4.3.4 Performance and Scale Validation

- [ ] Define expected workload profile (users, queries/min, upload sizes).
- [ ] Run load and soak tests in staging.
- [ ] Tune DB connection pooling and app workers.
- [ ] Document scaling triggers and actions.

## 4.4 Phase 4 - Intelligence Layer

### 4.4.1 Analytics Foundation

- [ ] Define cost metric catalog (mean, median, percentile, volatility).
- [ ] Implement inflation-adjusted cost normalization.
- [ ] Add regional and temporal benchmark views.
- [ ] Add confidence indicators on derived metrics.

Acceptance criteria:

- [ ] Analytics results are reproducible and trace back to source records.

### 4.4.2 Visualization and Reporting

- [ ] Add trend charts by item, location, and period.
- [ ] Add comparative views (region vs region, year vs year).
- [ ] Add export support for reports (CSV/PDF).
- [ ] Add saved query/report definitions.

Acceptance criteria:

- [ ] Core stakeholders can answer top 10 estimation questions without ad hoc SQL.

### 4.4.3 Predictive Capabilities

- [ ] Define target prediction use cases and baseline models.
- [ ] Implement train/validate/evaluate pipeline.
- [ ] Track feature lineage and model version metadata.
- [ ] Add model quality monitoring and retraining triggers.
- [ ] Publish explainability notes for prediction outputs.

Acceptance criteria:

- [ ] Model outperforms baseline heuristics by agreed threshold.
- [ ] Users can view factors that influenced each estimate.

## 5. Cross-Cutting Workstreams

## 5.1 Testing Strategy

- [ ] Unit tests for services and validators.
- [ ] Integration tests for API + DB + migrations.
- [ ] End-to-end tests for ingest/search/admin flows.
- [ ] Regression suite on every pull request.
- [ ] Test data fixtures for representative bid tabulation formats.

## 5.2 Data Quality Program

- [ ] Define quality rules and severity levels.
- [ ] Track quality score per ingestion run.
- [ ] Add monthly data quality review cadence.
- [ ] Feed recurring ingestion failures into parser improvements.

## 5.3 Documentation Program

- [ ] Keep architecture docs synchronized with implementation.
- [ ] Keep API docs and examples current.
- [ ] Maintain migration troubleshooting guide.
- [ ] Maintain release notes per version.

## 5.4 Schema Governance Program

- [ ] Publish canonical ERD (tables, PK/FK, cardinality, delete behavior).
- [ ] Document table naming convention and enforce singular/plural consistency.
- [ ] Keep schema doc synchronized with Alembic migrations on every release.
- [ ] Add schema drift check between models, migrations, and live database.
- [ ] Maintain seed-data catalog for reference tables (roles, permissions, units, project types, pipe use).

## 6. Milestones and Suggested Timeline

Use this as a planning baseline and adjust based on team capacity.

- [ ] M1 (Weeks 1 to 4): Phase 1 architecture, auth, schema, baseline API complete.
- [ ] M2 (Weeks 5 to 8): Phase 1 ingestion/search complete and MVP gate passed.
- [ ] M3 (Weeks 9 to 14): Phase 2 admin, governance, and ingestion reliability complete.
- [ ] M4 (Weeks 15 to 20): Phase 3 deployment, security hardening, observability complete.
- [ ] M5 (Weeks 21+): Phase 4 analytics and predictive pilot rollout.

## 7. Risk Register (Initial)

- [ ] Risk: heterogeneous source formats reduce ingestion reliability.
Mitigation: strict templates + parser fallback + per-row error isolation.

- [ ] Risk: query latency increases with data growth.
Mitigation: index strategy + query profiling + caching for hot paths.

- [ ] Risk: auth/role regressions expose sensitive data.
Mitigation: authorization test matrix + periodic permission audits.

- [ ] Risk: migration drift across environments.
Mitigation: CI migration checks + environment parity + rollback drills.

- [ ] Risk: schema inconsistency (FK names, missing RBAC bridge, ambiguous audit reference) causes delivery rework.
Mitigation: early schema normalization milestone + migration freeze window + ERD signoff.

- [ ] Risk: low trust in analytics/predictions.
Mitigation: traceable metrics + explainability + stakeholder validation loop.

## 8. Success Metrics (KPIs)

- [ ] Data ingestion success rate >= 95% (file-level) after template compliance.
- [ ] P95 search latency meets agreed target (for example, < 700 ms internal).
- [ ] Data quality error rate decreases sprint-over-sprint.
- [ ] Time-to-answer for common estimation questions decreases by 50%.
- [ ] Admin auditability: 100% of sensitive actions logged with actor + timestamp.

## 9. Long-Term Vision

```text
Historical Cost Repository
-> Operational Cost Intelligence System
-> Predictive Infrastructure Cost Decision Platform
```

Cost Query Pro should become the trusted source for historical and forward-looking infrastructure cost decisions, with strong data lineage, reproducible analytics, and production-grade reliability.
