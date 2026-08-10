# Deliverable 9 — Architecture Risks

Critical, evidence-based, not promotional. Theoretical problems unlikely to matter for the
intended application have been excluded — there is no complaint here about the absence of
microservices, event sourcing, or CQRS, because a modular monolith is the correct shape for this
system.

**Classification:**
- **[CURRENT]** — a live concern at today's scale and usage
- **[SCALING]** — fine now, breaks predictably as data or users grow
- **[MINOR]** — a real improvement, not urgent

---

## [CURRENT] concerns

### R-1 · Unbounded query and in-memory aggregation **[CURRENT → SCALING]**

`services/item_search.py:50` executes `query.all()` with **no `LIMIT`**, and
`services/analytics.py:39` materializes every matching row as an ORM object to build a Python
list of floats.

The keyword is chosen by an LLM. A question like *"what does pipe cost?"* yields
`ILIKE '%pipe%'`, which at 100k items may match most of the corpus. There is no statement
timeout, no pagination, and no truncation signal in `search_scope` — so a capped result, once
capping exists, would be silently indistinguishable from a complete one.

Compounding: `ILIKE '%…%'` cannot use a B-tree index, so it is a sequential scan regardless.

**Why it is [CURRENT] and not purely [SCALING]:** the input that triggers it is a *plausible user
question*, not a pathological one, and there is no rate limit in front of it.

**Fix:** `LIMIT` + statement timeout; report truncation in `search_scope`; move aggregation into
SQL (`func.percentile_cont`, `func.avg`) so rows never cross the wire. The trigram index is
already scoped in the roadmap.

---

### R-2 · The determinism guarantee starts one stage later than advertised **[CURRENT]**

The system's central claim is deterministic, auditable calculation. Precisely:

- **Deterministic:** the arithmetic, given a record set.
- **Not deterministic:** which records constitute that set.

`params.item` — chosen by an LLM from free text, with **no `temperature` set anywhere in the
codebase** — becomes `ILIKE '%{params.item}%'` and is the sole determinant of the result set. The
same question asked twice may produce `"8-inch PVC water main"`, `"8 inch PVC"`, or
`"PVC water main"`: three record sets, three medians, each computed flawlessly.

Worse for auditability: `SearchParameters` is **not persisted**. `llm_usage` records tokens and
cost per `request_id` but not the parameters. An answer from last month cannot be reproduced from
server-side state — only the parameters that *happen to still be in the response JSON the user
kept* can explain it.

**Genuine mitigations already present** (state these in the same breath): `search_scope` makes
the chosen parameters *visible* to the user, so surprising numbers are diagnosable; and the blast
radius is a wrong-scope answer, never a wrong-math answer or a data leak.

**Fix:** `temperature=0` on the parse call (one line, largest single win); persist
`SearchParameters` per `request_id`; deterministic pre-parse for pattern-matchable elements
(state names, years, units) so the LLM handles only the residue.

**This is the most important finding in the review** and the one to raise before the other
architect does.

---

### R-3 · No rate limiting or spend cap on a money-spending endpoint **[CURRENT]**

`POST /api/v1/agent/query` makes two paid LLM calls per request. There is no per-user limit, no
global limit, and no monthly cap. Any authenticated user can loop it; the only consequence is
more `llm_usage` rows.

The ledger, indexes, and pricing table are all built and correct — the *enforcement* is not. The
roadmap's own sequencing note is sharp and worth repeating: enforcement must live in a **route
dependency, not inside `complete()`**, because `intent_parser.py` catches broad exceptions and
relabels them `INTENT_PARSE_ERROR`, which `api/agent.py` converts to a **200** — a budget error
raised inside the pipeline would be silently returned to the user as a clarifying question.

**Fix:** `COUNT` and `SUM` over `llm_usage` in a route dependency. The indexes already exist.

---

### R-4 · Provenance is scope-level; record-level provenance is withheld from the authorized user **[CURRENT]**

`AgentQueryResponse` carries `record_count` and `search_scope` but names no source project. A
user cannot answer *"which 47 records?"*

The original business requirement was explicit (`docs/00_overview/00_business_scope.md` §3):
*"See the following projects for more details: &lt;project name&gt;, &lt;project number&gt;,
&lt;year&gt;, &lt;unit item cost&gt;"*.

**The cause is an over-application of the LLM-isolation rule.** Withholding records from the
**LLM** is correct and intended. Withholding them from the **authenticated human user** — who is
authorized to see every one of them via `GET /api/v1/items/search` — protects nothing. These are
two independent channels: the API response to the user and the payload to the third party.
Conflating them costs the system its primary auditability goal for no security benefit.

**Fix:** add an optional `source_records` array (project name, number, year, unit price) to
`AgentQueryResponse`, populated from `items` *after* the LLM call. The sanitizer is untouched;
the boundary is unchanged. This is the highest-value/lowest-risk change identified in the review.

---

### R-5 · Significant built architecture is unreachable, and the roadmap says it is done **[CURRENT]**

| Component | Size | State |
| --- | --- | --- |
| `services/agent_tools.py` | 319 lines, 4 tools, 27 tests | No route imports it |
| `config/prompts.py` | Full domain vocabulary prompt | Imported by nothing |
| `settings.agent_prompt_version` | — | Never read |
| `models/audit_log.py` + migration `b201b4cac42c` | Table exists | **Zero `AuditLog(` instantiations** |
| `models/system_setting.py` | — | Not in `models/__init__.py`; unreachable via `Base.metadata` |
| `migrations_old/` | Directory | Retired environment still in tree |

`docs/07_checklist/00_high_level_roadmap.md` §Agent Architecture and Tools marks the tools and
the domain prompt `[x]`. The tests pass, so CI does not catch it — the code is exercised in
isolation and never in a request.

**Two distinct harms.** Maintenance: 319 tested lines that cannot regress a user-visible behavior
consume review attention indefinitely. Trust: a roadmap that overstates completion is the artifact
another engineer will calibrate against, and one discovered discrepancy discounts everything else
in it.

**The audit log is the most consequential instance** — a governance control that exists as schema
and produces no rows. See R-8.

**Fix:** either wire them in or mark them explicitly as staged in the roadmap. The domain prompt
is the cheapest and most valuable to activate — merging its vocabulary into the intent parser
directly attacks R-2.

---

### R-6 · Retrieval is lexical substring matching **[CURRENT]**

`ILIKE '%{keyword}%'` is the entire retrieval strategy. `"8-inch PVC water main"` does not match
`8" PVC WM`, `PVC PIPE, 8 IN`, or `Water Main - PVC (8")` — all normal cross-agency variants.

The failure is **silent and asymmetric**: a missed record does not error, it lowers
`record_count` and shifts the median. A user seeing "12 records" cannot tell whether 12 is the
true population or 12 of 60 that happened to share a phrasing. Combined with R-2, both *which*
records and *how many* depend on a model's phrasing guess.

**Fix:** hybrid retrieval — pgvector embeddings over `item_description` unioned with `ILIKE`,
structured filters still applied deterministically in SQL. `run_search` is a clean seam; nothing
downstream changes.

---

### R-7 · LLM output constraints are advisory **[CURRENT]**

`response_generator.py:18-36` instructs the model to state the record count, quote the median and
average, note the range, and never invent data. Nothing verifies compliance; the text is returned
verbatim.

The small-sample rule — *"If record count is low (< 5), caution the user"* — lives in
`config/prompts.py`, **which is imported by nothing**. The live prompt has no such rule. A
3-record answer can therefore be delivered with the same confidence as a 300-record answer.

**Fix:** deterministic post-check — assert the answer contains `record_count`; assert every
currency figure in the prose appears in the `CostSummary`; and append a *system-generated*
small-sample warning when `record_count < 5` rather than asking the model to remember. Ten lines
converts a prompt instruction into a guarantee.

---

### R-8 · Audit logging is a table with no writer **[CURRENT]**

Login, purge, user deletion, and admin promotion produce `logger.info` lines to a DEBUG-level
file handler — not audit rows. `audit_logs` has a model and a migration and has never been
written to.

For a system whose stated purpose includes auditability and enterprise governance, this is the
widest gap between claim and implementation. Log files are not an audit trail: they rotate, they
are unstructured, and they are not queryable by actor or action.

The model also has both `created_at` and `timestamp` columns with identical `server_default` —
unresolved duplication in a schema nothing exercises.

**Fix:** write rows for login success/failure, purge, user delete, user promote, ingest, and
agent query. The table exists; this is a service function and six call sites.

---

### R-9 · Currency stored as binary floating point **[CURRENT, low impact]**

`Item.unit_price` is `Float` (`models/item.py:35`); `ArchivedItem.unit_price` likewise.
`schemas/item.py:20` accepts `Decimal` and then explicitly serializes back to `float`
(`item.py:27-28`), so precision is discarded at the boundary.

At two-decimal unit prices this will not produce a visibly wrong answer. It nonetheless
contradicts the "exact, auditable calculation" claim under scrutiny, and summing floats across
large result sets accumulates error. `NUMERIC` is the correct type for money and this is the kind
of thing another architect notices immediately.

**Fix:** migrate to `Numeric(12, 4)`; use `statistics` on `Decimal` or aggregate in SQL.

---

### R-10 · Observability is a DEBUG log file in the working directory **[CURRENT]**

`config/settings.py:13-17` calls `logging.basicConfig(level=DEBUG, …, FileHandler("cost_query_pro.log"))`
**at module import**, in every environment. Consequences: unstructured text logs, no rotation, a
repo-relative path, and `intent_parser.py:83` writing raw LLM output at DEBUG.

There are no metrics, no tracing, and no health signal beyond `GET /` returning `SELECT 1`. The
`request_id` correlation key is good and there is nothing to correlate *with*.

Note also that graceful degradation returns **200**, so parse failures and empty results are
invisible to HTTP error-rate monitoring — precisely the two failure modes an operator most wants
to trend.

**Fix:** structured JSON logging at INFO, rotation, no raw LLM output in production, and explicit
counters for parse-failure and no-result rates.

---

## [SCALING] concerns

### R-11 · Two sequential LLM calls with no timeout and no streaming

Latency is the sum of two round trips (2–8s typical). No timeout is configured on either call, so
a hung provider connection holds a request and a DB session indefinitely. `FallbackLLMProvider`
catches all `anthropic.APIError` including 4xx, so a deterministically-failing malformed request
retries against OpenAI and fails twice — doubling latency and cost on a call that could never
succeed.

**Fix:** explicit timeouts; restrict failover to 5xx/429/connection errors; route the parse call
to a cheaper, faster model.

---

### R-12 · Synchronous ingestion in the request path

`api/ingest.py:57` reads the entire upload into memory (**no size limit** — an open P1 item) and
`run_ingestion` processes every row synchronously with per-row queries in
`_get_or_create_project` and `_item_exists`. A 10,000-row file is 20,000+ round trips inside one
HTTP request. No job queue, no progress, no retry.

`UploadHistory.status` is free text (`"pending"`, `"success"`, `"partial"`) rather than a
constrained enum — a state machine is scoped in the roadmap but not built.

**Fix:** size limit with 413; batch the lookups; move to a background job with a status endpoint
when file sizes justify it.

---

### R-13 · Connection pool sized for a scale that does not exist

`db_pool_size=20`, `max_overflow=10` (`config/settings.py:87-90`) — 30 connections from a
single-process app. Harmless now; becomes a Postgres connection-limit problem if the app is
horizontally scaled without revisiting it.

---

### R-14 · `Project.state` is an unconstrained `String`

No length limit, no CHECK, no FK to a states table. Ingestion silently substitutes `"XX"` when a
state is not exactly two characters (`services/ingestion.py:72-73`) — a **silent data-quality
degradation** that produces no `DataQualityIssue` row, in a pipeline that otherwise records every
defect. Those records then never match any state filter.

This is the sharpest inconsistency in an otherwise disciplined ingestion design, and it is an open
roadmap item (Q-8).

---

## [MINOR] improvements

### R-15 · `"US"` overloaded as a sentinel on a domain field

`SearchParameters.state` is exactly 2 characters, with `"US"` meaning "all states"
(`item_search.py:40`). It is not a valid state code, so a user who types it gets all-states
behavior. `Optional[list[str]] = None` would be clearer and would unblock regional comparison
(see [Deliverable 7](07_extensibility.md) §9).

### R-16 · Hardcoded current year

`_CURRENT_YEAR = 2026` (`intent_parser.py:17`) feeds the prompt's default five-year window. In
2027 it silently produces the wrong window with no error. `datetime.now().year` is the fix; the
broader lesson is the risk of encoding policy in prompt text.

### R-17 · Two divergent search implementations

`api/items.py:47-64` and `services/item_search.py:31-48` both search items with overlapping
filters and different semantics — `items.py` uses `Item.unit == unit` (exact) while
`item_search.py` uses `ilike` (substring), and `items.py` re-joins `Item.project` up to three
times. `item_search.py`'s docstring explicitly notes it avoids that pattern. Two behaviors, one
concept.

### R-18 · Dashboard calls its own API over HTTP without credentials

`web/views/routes.py:22-24` opens an `httpx.AsyncClient` against `settings.api_base_url` and
requests `/items/search` with **no Authorization header**. That route requires auth, so this
returns 401 and the error body is passed to the template as `data`. Tests stub the client
(`test_web_views.py:21-34`), so the defect is masked.

Architecturally: a server-rendered view should call the service layer directly rather than making
a loopback HTTP call to itself.

### R-19 · Registration endpoint hand-parses content types

`api/auth.py:59-87` inspects `content-type` and branches between JSON and form parsing inside the
handler — while `deps/payloads.py` contains a `parse_user_create` dependency built for exactly
this and used nowhere. `login` and `login-json` are similarly duplicated, with the latter marked
*"can be removed later"*.

### R-20 · Tests mock the provider; no contract test against real SDK shapes

`ClaudeProvider.complete` reads `response.content[…].text` and `response.usage.input_tokens`;
`OpenAIProvider` reads `response.choices[0].message.content`. Every test substitutes a `MagicMock`
(`tests/unit_tests/test_llm_provider.py`), so an SDK response-shape change passes CI and fails in
production. The roadmap's own §Testing and Documentation lists the integration tests as
outstanding.

`intent_parser.py:87-100` also catches bare `Exception` around `model_validate_json`, converting
any error — including a genuine bug — into a user-facing clarifying question.

---

## Summary

| ID | Risk | Class | Severity |
| --- | --- | --- | --- |
| R-1 | Unbounded query, in-memory aggregation | CURRENT→SCALING | **High** |
| R-2 | Determinism starts after a non-deterministic parse; params not persisted | CURRENT | **High** |
| R-3 | No rate limit or spend cap on a paid endpoint | CURRENT | **High** |
| R-4 | Record-level provenance withheld from the authorized user | CURRENT | **High** |
| R-5 | Built architecture unreachable; roadmap overstates completion | CURRENT | **High** |
| R-6 | Lexical-only retrieval; silent recall failure | CURRENT | Medium-High |
| R-7 | LLM output constraints advisory; small-sample rule unwired | CURRENT | Medium |
| R-8 | Audit log table with no writer | CURRENT | Medium |
| R-9 | Currency as binary float | CURRENT | Medium-Low |
| R-10 | DEBUG file logging; no metrics; 200s hide failures | CURRENT | Medium |
| R-11 | Sequential LLM calls, no timeout, over-broad failover | SCALING | Medium |
| R-12 | Synchronous unbounded ingestion in the request path | SCALING | Medium |
| R-13 | Pool sized for unrealized scale | SCALING | Low |
| R-14 | Silent `"XX"` state fallback with no quality record | SCALING | Medium |
| R-15 | `"US"` sentinel on a domain field | MINOR | Low |
| R-16 | Hardcoded current year | MINOR | Low |
| R-17 | Two divergent search implementations | MINOR | Low |
| R-18 | Dashboard loopback call without credentials | MINOR | Low |
| R-19 | Hand-parsed content types; unused dependency | MINOR | Low |
| R-20 | No provider contract tests | MINOR | Medium |

### If only five things get fixed

1. **R-4** — return source records to the authenticated user. Highest value, lowest risk, restores
   the original auditability goal, does not touch the security boundary.
2. **R-3** — rate limit and spend cap in a route dependency. The ledger is built; only enforcement
   is missing.
3. **R-2** — `temperature=0` and persist `SearchParameters`. One line plus one table column
   converts *visible* provenance into *auditable* provenance.
4. **R-1** — `LIMIT`, statement timeout, aggregation in SQL.
5. **R-5** — wire in the domain prompt (which also improves R-2 and R-7), and correct the roadmap
   for everything still staged.

### What the architecture gets right, for balance

The LLM data boundary is genuinely strong and test-pinned. The provider abstraction is clean and
correctly attributes cost after failover. Ingestion's partial-success model with persisted quality
issues is the right design for dirty engineering data. The cost ledger was built before the
features that depend on it, which is the correct order. CI runs `mypy --strict`, Bandit, and the
full suite against real PostgreSQL. And the project's own audit process found and fixed two
genuine criticals — a weak-JWT-secret default and an irreversible purge — before this review
started.
