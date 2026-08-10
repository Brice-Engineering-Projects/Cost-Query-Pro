# Deliverable 6 — Security and Trust Model

Implemented controls and recommended controls are kept in separate sections throughout. Nothing
in §1 is aspirational; nothing in §3 exists.

---

## 1. Implemented controls **[IMPL]**

### 1.1 Authentication

| Control | Evidence |
| --- | --- |
| JWT bearer tokens, HS256 | `core/security.py:47-67` |
| bcrypt password hashing with per-password salt | `core/security.py:30-39` |
| Signing key required, minimum 32 bytes, startup fails without it | `config/settings.py:77` |
| Configurable token expiry (default 60 min) | `config/settings.py:103` |
| **User row re-loaded from DB on every request** | `core/security.py:91-94` |
| Minimum password length enforced at registration | `api/auth.py:92-97` |
| Admin self-registration gated by `allow_admin_signup`, default `False` | `api/auth.py:105`, `settings.py:105` |

The DB re-load on every request is the most security-relevant line here. It means a deleted
user's unexpired token fails — the system's only working revocation mechanism, achieved as a side
effect of a design choice rather than a denylist.

The `secret_key` requirement is a **remediated critical finding**, not an original design
property. It previously defaulted to the literal `"default_secret_key"` (18 bytes) while
`environment` defaulted to `"production"` — meaning an unconfigured deployment signed tokens with
a value published in this repository, and anyone reading it could forge an `is_admin` token and
reach the irreversible purge endpoint. Documented and fixed on 2026-07-30
(`docs/07_checklist/20260730_outstanding_items_checklist.md` P0/P2-C-2). Worth mentioning if
security-review process comes up: it was found by the project's own audit, not by an incident.

### 1.2 Authorization

| Control | Evidence |
| --- | --- |
| Every non-root route requires `get_current_user` | all `api/*.py` |
| Admin routes require `get_current_admin` → 403 | `core/security.py:97-101` |
| Purge is admin-only | `api/purge.py:26` |
| User management (list/delete/promote) is admin-only | `api/admin_users.py:25,41,71` |
| Admins cannot delete themselves | `api/admin_users.py:49-50` |

**Model:** two roles, one boolean (`users.is_admin`). No per-project, per-state, or per-agency
scoping — any authenticated user can query and read all cost data, and create/update/delete any
item or project (`api/items.py:87,115,146` require only `get_current_user`). Adequate for a
single trusted engineering team; insufficient for multi-department deployment. Roadmap scopes
`roles`/`permissions` tables for Phase 2.

### 1.3 LLM data boundary — the strongest control in the system

| Control | Evidence |
| --- | --- |
| Only `CostSummary` + 3 scope fields cross outward | `services/response_generator.py:39-61` |
| Payload built as a hand-written f-string, not a serializer | same |
| Intent parser has no DB access (no `Session` parameter) | `services/intent_parser.py:55` |
| Model output validated into Pydantic before use; `extra="ignore"` | `schemas/agent.py:8-16` |
| No SQL generation by the model anywhere | architectural |
| Empty result sets never reach the LLM | `api/agent.py:155-172` |
| Parse failures never reach the LLM (canned constant) | `api/agent.py:36-40` |
| Boundary pinned by test against 8 forbidden field names | `tests/unit_tests/test_response_generator.py:150` |

**Exhaustively, what leaves the environment:**

- Call 1: static system prompt + the user's question.
- Call 2: static system prompt + the user's question + `item`, `state`, year range + five numbers.

Never: project names, project numbers, contractor names, individual unit prices, quantities,
uploaded file contents, filenames, usernames, user IDs, or `request_id`.

The f-string construction is what makes this a *structural* guarantee. Adding a column to `Item`
cannot change this payload because no code here reads `Item`. Most "we sanitize before sending"
claims cannot survive being printed on a slide; this one is nine lines and can.

### 1.4 Injection resistance

**SQL injection: structurally prevented.** All queries are SQLAlchemy ORM expressions with bound
parameters (`services/item_search.py:31-48`). LLM output reaches the database only as a *value*,
never as syntax, and passes a Pydantic range check first. This is not input sanitization — it is
an architecture in which the injection vector does not exist.

**Prompt injection: present, small blast radius today.** The question is interpolated verbatim
into both prompts. There are no tools, no DB access from either call, and the sanitizer is
positional, so injected text cannot introduce new fields. Realistic attacks are self-directed —
a user manipulating the prose *they themselves* receive. This changes if tool-calling is wired in
(the code exists) or if any feature lets one user's input influence another's output.

**Path/file injection: not applicable.** Uploads are read into memory as bytes
(`api/ingest.py:57`) and never written to disk.

### 1.5 Data governance and auditability

| Control | State | Evidence |
| --- | --- | --- |
| Upload lineage: who, what file, when, outcome | **[IMPL]** | `models/upload_history.py` |
| Per-record source FK (`items.upload_id`, `SET NULL`) | **[IMPL]** | `models/item.py:38-42` |
| Per-row data-quality issues persisted | **[IMPL]** | `models/data_quality_issue.py` |
| LLM usage ledger: user, request, stage, provider, model, tokens, cost | **[IMPL]** | `models/llm_usage.py` |
| Purge archives to `archived_projects`/`archived_items` in one transaction | **[IMPL]** | `api/purge.py:49-84` |
| Purge records `purged_by_user_id` | **[IMPL]** | `api/purge.py:57` |
| Search scope returned on every agent response | **[IMPL]** | `api/agent.py:141-149` |
| `request_id` correlates response ↔ logs ↔ cost ledger | **[IMPL]** | `api/agent.py:98` |
| **`audit_logs` table** | **[PARTIAL]** | Model at `models/audit_log.py`, migration `b201b4cac42c` — **zero writes anywhere in `src/`** |

Purge transactionality is another remediated finding: purge was previously irreversible, and
the archive models had colliding `__tablename__` values that made them unusable. Fixed
2026-07-30 (`0d2c906`, `a532917`).

### 1.6 Supply chain and CI

`.github/workflows/ci.yml` gates every push and PR on: `pre-commit` (all files), **`mypy --strict`
on `src/cost_query_pro`**, **Bandit** on `src`, and the full pytest suite against a real
PostgreSQL 16 service container. `uv sync --frozen` enforces the lockfile. Dependabot is
configured. `pip-audit` remediation appears in the commit history (`bb66f54`).

`db/session.py:22-30` refuses to run when `TESTING=1` against any database that is not local and
not suffixed `_test` — a guard against the classic destructive-test accident.

---

## 2. Known gaps in implemented controls

Real, present, and worth stating before someone finds them.

| # | Gap | Evidence | Impact |
| --- | --- | --- | --- |
| G-1 | **No rate limiting on the agent endpoint.** An authenticated user can loop it indefinitely | no limiter in `src/` | Cost-exhaustion DoS. The ledger records the spend; nothing stops it |
| G-2 | **No monthly spend cap.** `LLM_MONTHLY_BUDGET_USD` is referenced only in the roadmap | not in `config/settings.py` | Unbounded third-party spend |
| G-3 | **`audit_logs` is never written.** Login, purge, user deletion, and promotion produce log lines, not audit rows | grep: zero `AuditLog(` instantiations | No queryable, tamper-evident record of privileged actions. The most significant governance gap |
| G-4 | **No upload size limit.** `await file.read()` loads the whole body into memory | `api/ingest.py:57` | Memory-exhaustion DoS. Tracked as an open P1 item |
| G-5 | **No unbounded-query protection.** `run_search` has no `LIMIT`; every match is materialized in Python | `services/item_search.py` | A broad question loads the corpus into memory |
| G-6 | **Logging at `DEBUG` to a repo-relative file.** `logging.basicConfig(level=DEBUG, FileHandler("cost_query_pro.log"))` runs at import of `config/settings.py`; `intent_parser.py:83` debug-logs raw LLM output | `config/settings.py:13-17` | Verbose logs written into the working directory in every environment; no rotation, no redaction, no structured format |
| G-7 | **`.env` is committed to the repository.** | `./.env` present in the tree | Depends entirely on contents; must be verified and, if it ever held live credentials, rotated. Check before any external demo |
| G-8 | **No HTTPS/TLS enforcement, no HSTS, no security headers** | none in `main.py` | Assumes a terminating proxy that is not documented |
| G-9 | **CORS allows `localhost:8000` with `allow_credentials=True`** | `main.py:77-83` | Correct for dev; the inline comment flags it for tightening before deployment |
| G-10 | **Dashboard makes an unauthenticated loopback HTTP call to its own API** | `web/views/routes.py:22-24` | `/items/search` requires auth, so this returns 401 and renders an error body as data. Masked in tests by a stubbed client (`test_web_views.py:21-34`). Architecturally, a server-rendered view should call the service layer directly, not its own HTTP surface |
| G-11 | **No token revocation or refresh flow** | `core/security.py` | A leaked token is valid for its full 60 minutes unless the user is deleted |
| G-12 | **`is_admin` is embedded in the JWT but not read on authorization** | `api/auth.py:36` writes it; `core/security.py:99` reads the DB | Benign — and actually the safer of the two orderings. Worth knowing so it is not mistaken for a stale-claim vulnerability |

---

## 3. Recommended future controls **[REC]** — none of these exist

Ordered by value per unit of effort.

### Priority 1 — before any multi-user internal deployment

1. **Rate limiting in a route dependency** — per-user and global, `COUNT` over `llm_usage` in a
   window. The indexes are already in place (`models/llm_usage.py:44-49`). Must live in a route
   dependency, **not** inside `complete()`: `intent_parser.py` catches broad exceptions and
   relabels them `INTENT_PARSE_ERROR`, which the endpoint converts to a **200** — a budget error
   raised inside the pipeline would be silently returned as a clarifying question.
2. **Monthly spend cap** — `SUM(cost_usd)` in the same dependency, with the same placement
   constraint. Note `cost_usd` is nullable by design, so the sum must handle NULLs explicitly.
3. **Write the audit log.** The table and migration exist. Emit rows for login success/failure,
   purge, user delete, user promote, ingest, and agent query. This closes G-3 and is the single
   highest-value governance change available.
4. **Upload size limit** with HTTP 413. Already an open P1 item.
5. **Query bounds** — `LIMIT` on `run_search` plus a statement timeout; surface truncation in
   `search_scope` so a capped result is visible rather than silent.

### Priority 2 — before external or regulated deployment

6. **Structured JSON logging** at INFO, with `request_id` on every line, no raw LLM output at
   DEBUG in production, rotation, and an explicit no-secrets policy. Replaces the import-time
   `basicConfig`.
7. **RBAC** — `roles`/`permissions` tables, replacing the `is_admin` boolean. Already scoped in
   the roadmap.
8. **Refresh tokens + revocation list**, shortening access-token lifetime.
9. **TLS enforcement and security headers** — HSTS, `X-Content-Type-Options`, `X-Frame-Options`,
   restrictive CORS.
10. **`.env.example`** with placeholders; verify and purge any real secret from history. Already
    an open P3 item.

### Priority 3 — hardening the AI boundary specifically

11. **Delimit the user question** in both prompts and instruct the model to treat it as data.
12. **Deterministic output post-check** — assert the answer contains `record_count`; assert every
    currency figure in the prose appears in the `CostSummary`; append a system-generated
    small-sample warning when `record_count < 5` rather than relying on prompt text.
13. **Persist `SearchParameters` per `request_id`** so an answer is reproducible from server-side
    state. Closes the gap between *visible* and *auditable* provenance.
14. **`temperature=0` on the parse call.** Currently unset; behavior follows each provider's
    default. Cheapest single improvement to reproducibility in the codebase.
15. **Enterprise no-egress mode** — template-rendered answers, eliminating LLM call 2 entirely.
    Already designed (`docs/03_api/01_secure_ai_query_architecture.md` §Future Enterprise
    Deployment) and enabled by the fact that `CostSummary` is already the only input to the
    narration step. This is a genuinely strong answer to "what if we can't send anything to a
    third party?" — the architecture reduces that to swapping one function.

---

## 4. Trust model summary

| Actor | Trusted with | Not trusted with |
| --- | --- | --- |
| Authenticated user | All cost data, all read/write on items and projects | Admin operations (purge, user management) |
| Admin | Everything, including irreversible-adjacent operations | — (no separation of duties) |
| **LLM provider** | The user's question; five aggregate numbers; three scope fields | Records, names, numbers, contractors, files, identities, DB access, SQL |
| LLM **output** | Nothing until validated | Direct use — everything passes a Pydantic gate |
| Uploaded file | Nothing | Per-row validated; failures isolated and persisted |

**The one-sentence version:** *the LLM is treated as an untrusted external service in both
directions — its output is validated before use, and its input is whitelisted by construction.*
That framing is defensible under scrutiny and is the right thing to lead with in a security
discussion.

**The honest counterweight:** the controls protecting *data* are strong; the controls protecting
*the service itself* — rate limiting, spend caps, size limits, query bounds — are absent. The
system is well defended against leaking data and poorly defended against being run up a bill.
That is an unusual and recoverable posture, and it is better to name it than to be asked.
