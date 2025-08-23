# Cost Query Pro — AWS + Snowflake Target Architecture (Senior-Dev Plan)

**Goal**: Keep FastAPI and your OLTP-style workflows on AWS while adding Snowflake as a scalable, governed analytics/query layer for CQP searches and reporting. No ML; pure SQL.

## High-Level Architecture

Users / Frontend → HTTPS (JWT) → FastAPI (uv)

**FastAPI responsibilities:**

* Authentication, API routing, validation, observability
* Writes/admin to OLTP (Postgres on AWS RDS)
* Reads/search to OLAP (Snowflake secure views)

**Data pipeline:**
* RDS Postgres → export to S3 → Snowflake STAGE → COPY INTO RAW → MERGE into CORE → exposed via SECURE VIEWS.

**Why this split:**

* RDS Postgres remains canonical for writes (transactions, admin CRUD).
* Snowflake handles analytics queries (scalable, concurrent, governed, low-ops).

---

## Snowflake Data Model

**Schemas:**

* RAW = landing tables from S3
* CORE = normalized tables (projects, items, users)
* VIEWS = secure views for API consumption
* Optional META = load history, pipeline logs

**Minimal DDL:**

* Database = CQP
* Warehouse = WH_CQP_XS (XSMALL, auto-suspend 60s, auto-resume)

**Tables:**
* Projects(id, project_name, project_number, state, year)
* Items(id, project_id, item_description, unit, unit_price)
* Users(id, username, password_hash, is_admin)
* Secure view V_ITEMS_SEARCH joins Items + Projects.
* Clustering keys: skip initially, add later if needed (e.g. on state/year).

---

## Ingestion Strategy (RDS → S3 → Snowflake)

### Option A – Batch:

* Nightly/hourly export from Postgres to S3 (Parquet).
* COPY INTO RAW then MERGE into CORE.

### Option B – Near-Real-Time:

* Use Snowpipe to auto-ingest on file arrival.

Merge pattern: MERGE RAW → CORE with upsert logic.

---

## Security & Governance

### Roles:

* CQP_APP (API): USAGE + SELECT on views only.
* CQP_ETL (loader): privileges on RAW and CORE.

Use Resource Monitors to cap monthly credits.
Secure views to hide sensitive columns or restrict row access.
Optional network policies for egress IP restrictions.

---

## FastAPI Integration

Principle: Postgres = writes, Snowflake = reads.

Connector: snowflake-connector-python or Snowflake SQLAlchemy dialect.
Dependency injection to open Snowflake sessions with role CQP_APP.
Search endpoint hits V_ITEMS_SEARCH with filters for q, state, year range.

DevOps on AWS

FastAPI: deploy on App Runner (simple) or Elastic Beanstalk (containerized).
Postgres: Amazon RDS (small instance for dev, scale later).
S3: staging bucket for exports.
Secrets: AWS Secrets Manager for Snowflake creds and DB URLs.
Observability: CloudWatch Logs; optionally parse Snowflake QUERY_HISTORY.

Cost Guardrails

Warehouse size = XSMALL, auto-suspend = 60s, auto-resume = TRUE.
Separate small warehouses for ingestion vs API queries if concurrency grows.
Resource monitor: e.g., 100 credits/month cap with alert at 80%.
Query hygiene: avoid SELECT *, push filters down, always LIMIT.

Rollout Plan

Phase 0: Setup Snowflake DB/SCHEMAs, warehouse, roles, S3 stage, IAM role.
Phase 1: Implement Postgres → S3 export, COPY + MERGE. Validate counts.
Phase 2: Add secure views, integrate Snowflake into FastAPI search endpoint (feature flag). Compare Postgres vs Snowflake results.
Phase 3: Enable auto-suspend, resource monitor, add monitoring/alerts.
Phase 4: Optional Snowpipe, clustering keys, additional secure views.

Packaging (uv / pyproject.toml)

Dependencies:
fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, psycopg, snowflake-connector-python, snowflake-sqlalchemy, boto3, pyarrow, pandas.

Environment variables:
Snowflake creds (user, password, account, role, warehouse).
Postgres DATABASE_URL.

Testing & Validation

Contract tests: ensure Snowflake query results = Postgres results for test fixtures.
Performance tests: measure cold vs warm warehouse latencies.
Data quality: row counts, checksums, spot checks.

Risks & Mitigations

Data drift: schedule loads, monitor load completeness.
Cost creep: use monitors and warehouse controls.
Cold-start latency: auto-suspend at 60s, consider minimum concurrency if 24/7 usage required.

Decision Summary

AWS is the platform for compute, networking, and hosting.
RDS Postgres remains the system of record for writes/admin.
Snowflake augments as the scalable read/query layer.
FastAPI search endpoints read from Snowflake secure views, giving scalability and concurrency with predictable cost.