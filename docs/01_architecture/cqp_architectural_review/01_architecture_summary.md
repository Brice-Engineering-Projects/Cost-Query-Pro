# Deliverable 1 — Architecture Summary

**Audience:** a technically sophisticated engineer who has never seen this repository.

---

## 1. What the system is

Cost Query Pro is a **single-process FastAPI modular monolith** over PostgreSQL that lets
engineers ask plain-English questions about historical construction unit costs and receive an
answer that states both the number and the search scope it came from.

Roughly 3,800 lines of application code across `src/cost_query_pro/`, ~3,300 lines of tests,
172 test functions. It is not a distributed system, and nothing in the current requirements
suggests it should be.

The one-sentence architectural thesis:

> **The LLM translates and narrates. The application computes.**

Everything distinctive about the design follows from taking that sentence literally.

---

## 2. The architectural pattern

There is no single textbook pattern, but the system is accurately described as the composition
of three:

### 2.1 Layered modular monolith (the whole system)

```
api/          HTTP boundary — routing, auth dependencies, error → HTTP mapping
services/     Business logic — the only layer that orchestrates
models/       SQLAlchemy ORM — persistence
schemas/      Pydantic — the contract between every pair of layers
config/       Settings, pricing tables, prompt text
core/         Cross-cutting: AppError, JWT/password primitives
```

Discipline is real: `api/` modules contain almost no logic beyond dependency wiring and
response shaping. `services/item_search.py` and `services/analytics.py` do not know an HTTP
request exists. `services/llm_provider.py` is the only module in the codebase that imports
`anthropic` or `openai` — a boundary I verified holds with no exceptions.

### 2.2 Sanitizing gateway / bulkhead (the AI subsystem)

The distinctive pattern. The LLM is treated as an **untrusted external service on both sides**:

- It is untrusted **as an input source** — its output is parsed into a Pydantic model
  (`SearchParameters`) before anything acts on it, and unparseable output degrades to a
  clarifying question rather than an error.
- It is untrusted **as a data recipient** — a fixed, hand-built five-field payload is the only
  thing that crosses outward.

There is no place in the system where an LLM response is used without passing through a
schema, and no place where a database row reaches a prompt.

### 2.3 Pipes-and-filters (the query path)

Five fixed stages, no branching, no loops, no agentic control flow. This is a deliberate and
consequential choice — see [Deliverable 4](04_architectural_decisions.md), Decision 3.

---

## 3. System boundaries and who owns what

### Boundary A — HTTP / authentication

**Owner:** `api/*.py`, `core/security.py`
**[IMPL]** Every non-root route depends on `get_current_user` (JWT HS256, bcrypt password
hashes). Admin routes add `get_current_admin`. `AppError` is the single structured error type;
`main.py:86-115` maps it, `HTTPException`, and `RequestValidationError` to consistent JSON
`{code, message}` bodies.

**Explicitly not owned here:** business rules, query construction, statistics. The API layer
is thin by design and stays thin in practice.

### Boundary B — Ingestion

**Owner:** `services/ingestion.py`, `api/ingest.py`
**[PARTIAL]** Accepts CSV and XLSX. Normalizes headers case-insensitively, validates required
columns file-wide and field values per row, isolates row failures, deduplicates on
`(project_number, item_description, unit)`, and writes lineage.

PDF is **[PLANNED]**: `pdfplumber>=0.10` and `pdfminer-six` are declared in `pyproject.toml:23,34`
and the extraction requirements are specified in the roadmap, but no PDF code path exists.
`api/ingest.py:34-38` rejects anything that is not `.csv` or `.xlsx`.

The genuinely notable design choice here is **partial success as a first-class outcome**. A
file is not accepted or rejected — it produces an `IngestReport` with inserted / skipped /
failed counts and a per-row issue list, and every failure is *persisted* as a
`DataQualityIssue` row keyed to the upload. This is the correct model for engineering source
data, where a 500-row bid tab with 3 malformed rows is normal, not exceptional.

### Boundary C — Persistence

**Owner:** `models/`, `db/session.py`, Alembic under `migrations/`
**[IMPL]** `Project 1→N Item` is the core relation. Around it sits a lineage and governance
ring: `UploadHistory` (who uploaded what, when, with what outcome), `DataQualityIssue` (why
rows failed), `LlmUsage` (what each AI call cost), `ArchivedProject`/`ArchivedItem` (purge
recovery).

`items.upload_id` is a nullable FK with `ON DELETE SET NULL` — every stored cost record can be
traced to the file it came from, and deleting the upload record degrades lineage rather than
destroying the cost data. That is the right tradeoff for this domain.

### Boundary D — The deterministic core

**Owner:** `services/item_search.py`, `services/analytics.py`
**[IMPL]** `run_search()` takes a validated `SearchParameters` and returns ORM objects.
`compute_summary()` takes those objects and returns a `CostSummary`. Neither module imports an
LLM SDK, touches HTTP, or reads settings. They are the most reusable code in the repository.

### Boundary E — The AI boundary

**Owner:** `services/llm_provider.py`, `intent_parser.py`, `response_generator.py`
**[IMPL]** A `Protocol`-typed `LLMProvider` interface with four implementations:
`ClaudeProvider`, `OpenAIProvider`, `FallbackLLMProvider` (Claude → OpenAI on `anthropic.APIError`),
and `MeteredProvider` (a decorator recording every completion). A fresh provider is constructed
per request via `Depends(get_llm_provider)`, which is what makes per-request accumulation on
`MeteredProvider.calls` safe.

### Boundary F — Cost accounting

**Owner:** `services/usage_recorder.py`, `models/llm_usage.py`, `config/pricing.py`
**[IMPL]** One `llm_usage` row per *completion*, not per request — because one query makes two
calls and a failover can split those across two providers at different rates. Usage is recorded
on all four exit paths of `api/agent.py`, including both graceful-degradation returns, because
an ambiguous question still costs money. `record_usage` catches and swallows its own failures
(`usage_recorder.py:65-72`): accounting must never turn a good answer into a failed request.

Unpriced models record a **NULL** `cost_usd` rather than `0.0` (`config/pricing.py:56-70`), which
keeps "we don't know the price" distinguishable from "this was free" when summing a monthly
total. This is a small decision that signals genuine care about the integrity of a spend ledger.

---

## 4. The two lifecycles

The system has two independent flows that meet only at the database. Conflating them is the
most common way to misread this architecture.

**Write lifecycle (human-initiated, batch, admin-ish):**
File upload → parse → validate → normalize → dedupe → persist + lineage → structured report.
No LLM involvement anywhere.

**Read lifecycle (interactive, per-question):**
Question → LLM parse → deterministic search → deterministic aggregation → sanitize → LLM narrate
→ answer + scope. No writes except the usage ledger.

---

## 5. What the architecture is optimized for

In priority order, as evidenced by where the design effort went:

1. **Not letting the LLM be wrong about numbers.** Arithmetic is `statistics.median()` on
   Python floats, never a token prediction.
2. **Not letting proprietary cost data leave the building.** The sanitizer is a hand-built
   string, not a serializer — you cannot accidentally add a field to it.
3. **Being able to explain where a number came from.** `search_scope` is returned on every
   response, including the empty and ambiguous paths.
4. **Knowing what the AI costs.** The usage ledger predates the features it was built to
   support (rate limiting, spend caps), which is the correct build order.

---

## 6. What the architecture is *not* optimized for, and knows it

- **Scale.** `run_search()` has no `LIMIT` and aggregation happens in Python, not SQL. Fine at
  thousands of rows; a real problem at millions. See [Deliverable 9](09_architecture_risks.md), R-1.
- **Reproducibility of *scope*.** Reproducibility of *arithmetic* is guaranteed. Reproducibility
  of *which records were selected* is not, because an LLM picks the keyword. See
  [Deliverable 5](05_ai_architecture.md) §4.
- **Record-level citation.** Deliberately excluded from LLM payloads — correct. Also absent from
  the API response to the authenticated user — an over-application. See
  [Deliverable 9](09_architecture_risks.md), R-4.

---

## 7. Honest summary of maturity

| Subsystem | State |
| --- | --- |
| Auth (JWT, bcrypt, admin flag) | **[IMPL]** — solid, binary roles only |
| CSV/Excel ingestion + lineage | **[IMPL]** — the most complete subsystem |
| PDF ingestion | **[PLANNED]** — deps declared, requirements specified, no code |
| Deterministic search + analytics | **[IMPL]** — clean, unbounded |
| LLM provider abstraction + failover | **[IMPL]** — genuinely well-factored |
| Two-call secure pipeline | **[IMPL]** — the boundary holds |
| Tool-calling agent (4 tools) | **[WIRED-OFF]** — built and tested, no caller |
| Domain vocabulary prompt | **[WIRED-OFF]** — never imported |
| Token/cost ledger | **[IMPL]** |
| Rate limiting, spend cap | **[PLANNED]** — ledger exists, enforcement does not |
| Purge → archive recovery | **[IMPL]** — transactional as of `a532917` |
| Audit log | **[PARTIAL]** — table and migration exist, zero writes |
| RBAC beyond `is_admin` | **[PLANNED]** |
| Snowflake OLAP read path | **[PLANNED]** — design doc only |

**One-line verdict:** the query path is a well-reasoned, correctly-bounded design whose
principal weakness is that its non-deterministic front door partly undercuts the determinism
guarantee it advertises; and whose principal presentation risk is that several of its most
impressive pieces are not actually running.
