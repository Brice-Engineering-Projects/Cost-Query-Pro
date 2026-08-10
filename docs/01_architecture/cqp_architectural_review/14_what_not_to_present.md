# Deliverable 14 — What Not to Present

**Principle.** In a 30-minute meeting with ~13 minutes of presentation, every minute spent on
something that is not an architectural decision is a minute stolen from the discussion that
justifies the meeting. The test for inclusion is: *does this reflect a decision that could have
gone another way, with consequences?* Framework configuration, CRUD, and utility code fail that
test regardless of how well written they are.

Three categories below: **omit entirely**, **hold in reserve**, and **must be volunteered** — the
last being things that would be worse to have discovered than disclosed.

---

## 1. Omit entirely

### 1.1 Framework and tooling configuration

`pyproject.toml`, `setup.cfg`, `alembic.ini`, `.pre-commit-config.yaml`, `.yamllint.yml`,
`dependabot.yml`, `uv.lock`, `.python-version`

FastAPI, SQLAlchemy, Alembic, uv, ruff, mypy — a conventional and well-assembled Python stack. It
signals competence and consumes time without conveying a decision. Another engineer assumes a
sane toolchain until shown otherwise.

**One exception, and only if CI process comes up:** `.github/workflows/ci.yml` gates every push on
`mypy --strict`, Bandit, and the full suite against a real PostgreSQL 16 service container. That
is above average and worth exactly one sentence.

---

### 1.2 CRUD endpoints

`api/items.py`, `api/projects.py`, `api/admin_users.py`

Standard REST over two tables. `api/items.py:87-161` is create/update/delete with a not-found
check. `api/admin_users.py` is list/delete/promote.

Two things inside them are worth knowing but not presenting: `api/items.py:47-64` duplicates
search logic that `services/item_search.py` implements differently (exact vs. substring unit
matching, and a triple join the service version explicitly avoids); and every item write route
requires only `get_current_user`, so any authenticated user can modify any cost record. The second
belongs in the authorization conversation if one happens, not in a walkthrough.

---

### 1.3 Authentication implementation detail

`core/security.py`, `api/auth.py`, `schemas/auth.py`, `schemas/token.py`, `deps/payloads.py`

JWT HS256 with bcrypt is the expected answer. Presenting it invites a tangent about token
lifetimes and refresh flows that has nothing to do with the AI architecture.

Actively avoid showing `api/auth.py:59-87`, where the register handler hand-inspects
`content-type` and branches between JSON and form parsing — while `deps/payloads.py` contains a
`parse_user_create` dependency built for exactly that purpose and used nowhere. Also avoid
`login` / `login-json`, duplicated endpoints with the latter commented *"can be removed later."*
Both are minor debt; neither is architecture.

**One sentence if authorization comes up:** two roles, one boolean, no per-project or per-agency
scoping; RBAC is scoped in the roadmap.

---

### 1.4 Model and schema definitions

`models/*.py`, `schemas/*.py`

`Project 1→N Item` conveys the whole data model in one line. Reading column lists is the least
efficient possible use of the time.

**Do not open `models/audit_log.py`** — it carries both `created_at` and `timestamp` with
identical `server_default`, and the table is never written to. Neither observation helps a
boundaries discussion. (The *absence* of audit logging is a different matter — see §3.)

---

### 1.5 The web UI

`web/views/routes.py`, `templates/base.html`, `templates/dashboard.html`

Two Jinja2 templates and one route. It is not the product surface — the API is — and
`routes.py:22-24` makes an **unauthenticated loopback HTTP call to its own API** for a route that
requires auth, so it returns 401 and renders the error body as data. The test suite stubs the
client, which masks it.

Showing this invites a discussion of an architectural mistake that is incidental to everything
being presented. Fix it later; skip it now.

---

### 1.6 Utilities, retired code, and generated artifacts

`utils/debug_url.py`, `migrations_old/`, `cost_query_pro.log`, `.idea/`, individual migration files

`migrations_old/` is a retired Alembic environment still in the tree.
`docs/05_db_and_migrations/01_README_debugging_alembic.md` documents a past migration debugging
episode. Both are project history, not architecture. `.idea/` is IDE configuration and is
committed — housekeeping, not a talking point.

---

### 1.7 Internal process documentation

`docs/08_diary_logs/`, `docs/09_audit_reports/`, `docs/07_checklist/20260730_outstanding_items_checklist.md`

Diary logs, audit reports, and remediation checklists are internal process artifacts. The audit
reports in particular describe two remediated criticals — a weak JWT secret default and an
irreversible purge — and volunteering old vulnerabilities unprompted reframes the meeting around
past defects.

**If engineering process comes up**, one sentence is the right amount: *"We run periodic
self-audits; the last two found a weak-secret default and an irreversible purge, both fixed in
July."* That is a strength, stated once, not a document to walk through.

---

## 2. Hold in reserve — bring out only if asked

These are substantive. They are omitted for time, not for weakness. Have them ready.

| Topic | Where | Trigger |
| --- | --- | --- |
| **Tool-calling implementation** (4 tools, 27 tests, unwired) | `services/agent_tools.py` | *"How would you handle multi-part questions?"* Present as **designed and staged**, never as operating |
| **Domain vocabulary prompt** (unwired) | `config/prompts.py` | *"How does it know what 'large diameter' means?"* Strongest content in the repo; be explicit it is not in the live prompt |
| **Cost ledger schema and pricing** | `models/llm_usage.py`, `config/pricing.py` | *"What does a query cost?"* The NULL-for-unpriced-models decision is a good detail |
| **Provider failover mechanics** | `services/llm_provider.py:157-195` | *"What if Anthropic is down?"* Include the observed-model attribution fix |
| **Purge-to-archive transactionality** | `api/purge.py:49-84` | *"How do you handle data lifecycle?"* |
| **Test-DB safety guard** | `db/session.py:22-30` | *"How do you test against Postgres?"* Refuses non-local, non-`_test` databases |
| **Snowflake OLAP design** | `docs/01_architecture/02_cqp_snowflake_architecture.md` | *"How would this scale?"* **[PLANNED]** — design only, no code, no dependency |
| **Graceful degradation paths** | `api/agent.py:121-174` | *"What happens when it fails?"* Genuinely good; also mention the bare-`Exception` catch |
| **Footer `project_number` requirements** | Roadmap §Footer-Based Extraction | *Any* ingestion question — and offer it proactively if they ingest bid tabs |

---

## 3. Must be volunteered

Discovering these unprompted costs more credibility than disclosing them. Each takes one sentence.

### 3.1 PDF ingestion is not implemented

Declared dependencies, written requirements, no code path. `api/ingest.py:34-38` rejects PDF.
Multi-format ingestion *was* an intentional early design consideration — it appears in the
earliest scope documents — and it is still unbuilt. Say both halves.

### 3.2 The tool layer and domain prompt are not wired in

`services/agent_tools.py` and `config/prompts.py` are built, tested, and reachable from no route.
The roadmap marks both complete. Anyone who opens `api/agent.py` sees the two-call pipeline in two
minutes, and one discovered overstatement discounts everything else said in the meeting.

### 3.3 There is no rate limit or spend cap

The ledger is built and correct; enforcement is not. An authenticated user can loop a
money-spending endpoint. This surfaces the moment cost is discussed, and volunteering it lets you
also explain the sequencing reasoning — measure first, then size the cap — which is the right
build order.

### 3.4 Determinism starts after the intent parse

The arithmetic is exact; which records get counted is an LLM's choice. Raise it on slide 9, before
they find the seam. See [Deliverable 9](09_architecture_risks.md) R-2.

### 3.5 Provenance is scope-level, not record-level

The response names no source project. The original business requirement asked for one. Frame it
accurately: an over-application of the LLM-isolation rule to a channel that does not need it.

---

## Quick reference

| Never | Only if asked | Always volunteer |
| --- | --- | --- |
| Config files, `uv.lock`, `.idea/` | Tool-calling layer (staged) | PDF not implemented |
| CRUD endpoints | Domain prompt (unwired) | Tools/prompt not wired in |
| Auth implementation | Cost ledger schema | No rate limit or cap |
| Model/schema listings | Provider failover mechanics | Determinism starts after parse |
| Web UI and templates | Purge transactionality | Provenance is scope-level |
| `migrations_old/`, utils | Snowflake design (planned) | |
| Diary logs, audit reports | Footer `project_number` problem | |

---

## The rule underneath all of this

**Present decisions, not code.** The only code that belongs on a screen is the nine-line sanitizer
in `services/response_generator.py:39-61`, and it belongs there precisely because its *brevity* is
the argument — a security control you can read in full in thirty seconds is a different kind of
claim than one you have to trust.

Everything else is either a decision (say it), a detail (hold it), or a gap (volunteer it). If a
question cannot be answered without opening an editor, the honest response is *"let me send you
the repo"* — and then the meeting stays where it is useful.
