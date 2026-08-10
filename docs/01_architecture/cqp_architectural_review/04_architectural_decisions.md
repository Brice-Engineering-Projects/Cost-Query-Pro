# Deliverable 4 — Major Architectural Decisions

Ten decisions, ordered by how much of the system's shape they determine. Each carries an
evidence label from [`00_README.md`](00_README.md#evidence-legend).

---

## Decision 1 — The LLM is a translator and narrator, never a calculator **[IMPL]**

**Decision.** All arithmetic and record selection execute in application code. The LLM is called
exactly twice: once to turn a question into structured parameters, once to turn computed numbers
into prose. It never sees a database row and never produces a number that reaches the user
unverified.

**Problem.** Language models are pattern predictors. Asked to average 47 prices they will produce
a plausible number, sometimes the right one, with no way for the user to tell which. In cost
estimating that number lands in a bid, and a wrong one is a commercial loss. The failure is also
*silent* — a hallucinated average looks exactly like a correct one.

**Benefit.** The number is `statistics.median()` over concrete rows (`services/analytics.py:39-47`).
Exact, repeatable given the same input set, and invariant across model, provider, temperature, and
prompt version. The system can change LLM vendors without a regression test on arithmetic. It is
also cheap: aggregates are a handful of tokens where raw records would be tens of thousands.

**Tradeoff.** The system can only answer questions the deterministic layer already implements.
There are five statistics available; a user asking "how has this trended since 2019?" gets an
answer scoped to min/median/mean/max because trend analysis does not exist in `analytics.py`.
Every new analytical capability is a code change, not a prompt change. This is the price of the
guarantee, and it is the right price.

**Enterprise relevance.** This is the difference between a tool an estimating department can use
for real work and a demo. It is also the answer to the first question any risk or legal function
asks about internal AI: *can it be wrong about a number?* Here the honest answer is no — it can be
wrong about *which* numbers, which is a different and more tractable problem.

---

## Decision 2 — Raw records never enter an LLM payload; the sanitizer is hand-built **[IMPL]**

**Decision.** The outbound payload for the narration call is a hand-written f-string containing
the user's question, three scope fields, and five numbers (`services/response_generator.py:39-61`).
No serializer, no `model_dump()`, no iteration over an ORM object.

**Problem.** Bid pricing is competitively sensitive. Project numbers, contractor names, and
per-project unit prices are exactly what an organization cannot send to a third-party API. The
usual mitigation — filter fields before serializing — fails open: add a column to `Item`, and it
appears in the next `model_dump()` with nobody noticing.

**Benefit.** Whitelisting by construction. You cannot leak a field that no line of code writes.
Adding a column to `Item` cannot change this payload, because nothing here reads `Item`. This
is a structural guarantee rather than a procedural one, and it is the strongest security property
in the codebase. Pinned by
`tests/unit_tests/test_response_generator.py:150`.

**Tradeoff.** Manual and rigid. Every new statistic requires editing the string. It also means
the LLM has genuinely thin context — it cannot say "prices cluster bimodally around $40 and $70"
because it never sees a distribution. Some real analytical nuance is sacrificed for the guarantee.

**Enterprise relevance.** Turns a hard security conversation into a short one: you can print the
function on a slide, and it is nine lines. Most "we sanitize before sending to the LLM" claims
cannot survive that. This one can, and the *auditability of the control itself* is worth as much
as the control.

---

## Decision 3 — A fixed two-call pipeline instead of an agentic tool-calling loop **[IMPL]**, with **[WIRED-OFF]** tooling

**Decision.** `api/agent.py` executes five stages in a straight line with no branching, no
iteration, and no model-directed control flow. Exactly two LLM calls per query, always.

**Note this carefully.** A complete tool-calling implementation exists —
`services/agent_tools.py` defines four Anthropic-format tools (`keyword_search`, `filter_search`,
`price_stats`, `project_lookup`), all with backend handlers and 27 passing tests. **No route
calls any of it.** Likewise `config/prompts.py`, which holds the entire domain vocabulary system
prompt, is imported by nothing. The roadmap marks both complete
(`docs/07_checklist/00_high_level_roadmap.md` §Agent Architecture and Tools); the request path
does not use them.

**Problem.** Agentic loops have unbounded cost, unbounded latency, and non-deterministic call
counts. For a cost lookup that resolves to one query, that variance buys nothing.

**Benefit.** Predictable cost (exactly two completions — makes the spend model trivially
computable), predictable latency, trivially testable control flow, and no possibility of the
model looping on a tool. It is also *complete* in the sense that matters: the two-call pipeline
answers the product's actual question.

**Tradeoff.** Multi-part questions ("compare PVC and ductile iron in Florida and Texas") cannot
be decomposed — the parser must collapse them into one `SearchParameters`, and it will silently
pick one interpretation. This is the main functional ceiling of the current design, and the
wired-off tools are exactly the thing that would lift it.

**Enterprise relevance.** Predictable per-query cost is what makes internal chargeback and
budgeting possible. "Two calls, ~1,500 tokens, roughly $0.01" is a sentence a platform team can
build a quota around. "It depends how many tools the model decides to call" is not.

---

## Decision 4 — LLM output is validated into a Pydantic model before anything acts on it **[IMPL]**

**Decision.** The intent parser's output passes through `SearchParameters.model_validate_json()`
(`services/intent_parser.py:88`). Failure produces `AppError("INTENT_PARSE_ERROR")`, which the
endpoint converts to a **200 with a clarifying question** rather than an error.

**Problem.** Model output is untrusted input. It may be prose, fenced JSON, JSON with extra keys,
or JSON with values outside any sane range. Acting on it directly is the same class of mistake as
trusting a form field.

**Benefit.** Three defenses in one gate. Type safety: everything downstream has a validated
`SearchParameters`. Range safety: `state` is exactly 2 chars, years are 1900–2100, prices are
non-negative — a model that emits `year_start: 1` is rejected, not queried on. Injection safety:
values become bound SQLAlchemy parameters, never SQL syntax. `extra="ignore"` drops unexpected
keys instead of propagating them. `_strip_code_fences()` (`intent_parser.py:46`) handles the
real-world behavior of models fencing JSON they were told not to fence.

**Tradeoff.** A rigid schema cannot express what users actually ask. Multi-state, multi-item, and
relative-time questions have no representation, so they degrade to a clarifying question or a
silently narrowed search. The 200-not-4xx choice is right for UX and does mean parse failures do
not surface in HTTP error-rate monitoring — they need a dedicated metric, which does not exist yet.

**Enterprise relevance.** "We validate model output against a schema before executing on it" is
the control an AI-governance review is looking for. Most internal LLM integrations cannot claim
it.

---

## Decision 5 — Multi-format ingestion was designed in from the start; PDF is specified, not built **[PARTIAL]**

**Decision.** Ingest engineering artifacts in the formats they already exist in — Excel, CSV,
PDF — rather than requiring engineers to restructure their work around the tool.

**Evidence that this was intentional and early, not retrofitted:** PDF appears in the earliest
scope document (`docs/00_overview/00_business_scope.md` §4, §6, §15), in the original architecture
overview as a named component with tool selection (`docs/01_architecture/01_architecture_overview.md`
§4), and `pdfplumber>=0.10` plus `pdfminer-six` are declared dependencies (`pyproject.toml:23,34`).

**Current state, stated plainly:** CSV and XLSX are implemented (`services/ingestion.py:35-59`).
PDF is not. `api/ingest.py:34-38` rejects it. The roadmap scopes it as Phase 2 with detailed
extraction requirements.

**Problem.** Historical bid tabs, engineer's estimates, and contractor pricing frequently exist
*only* as PDF. A system that cannot read them cannot see the majority of the historical record,
and asking engineers to re-key them means the system never gets populated.

**Benefit.** The ingestion service is already shaped for it. `run_ingestion()` takes
`content: bytes` and a `file_type` discriminator, dispatches to a parser, and every downstream
stage — validation, dedupe, lineage, quality issues — operates on a normalized
`list[dict[str, Any]]`. Adding PDF is one parser function plus a dispatch branch. The architecture
made the right accommodation even though the feature has not landed.

**Tradeoff.** PDF is qualitatively harder than the other two: table extraction is heuristic and
layout-dependent, and the roadmap has already identified the specific failure mode — bid tabs
routinely place `project_number` in a page footer rather than a column
(`docs/07_checklist/00_high_level_roadmap.md` §Footer-Based Project Number Extraction). Bolting
that onto a row-oriented pipeline requires document-level context the current design does not
carry. That is real design work, and it is honest to say it is ahead rather than behind.

**Enterprise relevance.** This decision determines whether the tool gets adopted. Any system
requiring re-keying of historical data does not get populated, does not get used, and dies. The
format list is an adoption strategy expressed as an architecture.

---

## Decision 6 — Ingestion treats partial success as a first-class outcome **[IMPL]**

**Decision.** A file is not accepted or rejected. Each row is validated independently; failures
are isolated, counted, and **persisted** as `DataQualityIssue` rows keyed to the upload; the
response is a structured `IngestReport` with inserted / skipped / failed counts plus a per-row
issue list (`services/ingestion.py:176-258`).

**Problem.** Bid tab data is genuinely dirty — merged cells, subtotal rows, notes in numeric
columns, inconsistent units. All-or-nothing ingestion means a 500-row file with 3 bad rows
produces zero rows and an unactionable error.

**Benefit.** 497 rows land, and the operator gets exactly which 3 failed and why. Because issues
persist rather than only appearing in the response, recurring problems become queryable — the
model docstring names the intended use: detecting patterns of format problems from particular
agencies (`models/data_quality_issue.py:5-8`). That is a data-governance capability, not just
error handling.

**Tradeoff.** Partial state is harder to reason about than atomic state. A re-upload after fixing
3 rows relies on the dedupe key `(project_number, item_description, unit)` to skip the 497 already
present — which works, but means correctness of re-ingestion depends on a dedupe rule that cannot
distinguish two legitimately different line items with the same description and unit in one
project. `status` is also free text (`"pending"`, `"success"`, `"partial"`) rather than a
constrained enum; the roadmap flags this.

**Enterprise relevance.** Determines whether ingestion is self-service. If an engineer can upload,
read a report, fix three cells, and re-upload without involving a developer, the system scales
across a department. Otherwise every file becomes a support ticket.

---

## Decision 7 — Ingestion lineage is schema, not logging **[IMPL]**

**Decision.** `UploadHistory` records who uploaded which file when with what outcome;
`items.upload_id` is a real FK from every cost record back to its source upload
(`models/item.py:38-42`), with `ON DELETE SET NULL`.

**Problem.** "Where did this $52.40 come from?" is unanswerable if provenance lives in log files
that rotate. In cost estimating, the question arrives months later, often adversarially, and
"check the logs" is not an answer.

**Benefit.** Provenance is queryable with a join and survives log rotation. Every price traces to
a filename, a user, and a timestamp. `ON DELETE SET NULL` rather than `CASCADE` is the right call:
deleting an upload record degrades lineage instead of destroying cost data.

**Tradeoff.** Storage overhead and a write on every ingest. Coverage is also incomplete — items
created directly through `POST /api/v1/items/` (`api/items.py:87`) have `upload_id = NULL` and no
provenance at all. Two write paths, one lineage mechanism.

**Enterprise relevance.** This is the substrate for a data-governance story: retention by source,
targeted rollback of a bad upload, per-agency quality reporting. None of that is built, and none
of it is *possible* without this schema.

---

## Decision 8 — Provider abstraction with metering and observed-model attribution **[IMPL]**

**Decision.** A `Protocol`-typed `LLMProvider` interface with four implementations —
`ClaudeProvider`, `OpenAIProvider`, `FallbackLLMProvider` (Claude → OpenAI on `anthropic.APIError`),
and `MeteredProvider`, a decorator recording every completion. `services/llm_provider.py` is the
only module in the codebase importing `anthropic` or `openai`.

**Problem.** Two distinct risks. Vendor lock-in: SDK calls scattered through business logic make
provider changes a rewrite. Vendor outage: a single-provider dependency means the product is down
when the provider is.

**Benefit.** Provider substitution touches one file. Failover is transparent to the pipeline —
`intent_parser.py` and `response_generator.py` do not know failover exists. `MeteredProvider`
composes cleanly as a decorator rather than threading token counting through business logic.

The detail worth highlighting: usage is attributed to the provider that **actually served the
call**, read from the last recorded completion rather than from configuration
(`api/agent.py:55-71`, `llm_provider.py:30-44`). Before this fix, a request that failed over to
OpenAI was billed at Anthropic rates. The commit history shows this was found and corrected
(`docs/07_checklist/00_high_level_roadmap.md` §Cost Control, step 1). It is a small bug whose fix
demonstrates that the cost ledger is meant to be trusted.

**Tradeoff.** The interface is the intersection of what both SDKs support — `complete(messages,
system, max_tokens)`. Provider-specific capabilities (tool use, streaming, prompt caching,
extended thinking) are inaccessible without widening it, which is part of why the tool-calling
path is not wired in. `FallbackLLMProvider` also catches all `anthropic.APIError` including 4xx,
so a malformed request retries against OpenAI and fails twice, doubling latency on a
deterministically-failing call. No `temperature` is set anywhere, so parse behavior depends on
each provider's default.

**Enterprise relevance.** Procurement changes vendors. Legal changes vendors. Outages happen.
A one-file provider swap is the difference between a policy change and a project.

---

## Decision 9 — Token/cost accounting built before the features that consume it **[IMPL]** → **[PLANNED]**

**Decision.** `llm_usage` records one row per completion — not per request — with
`(user_id, request_id, stage, provider, model, input_tokens, output_tokens, cost_usd, created_at)`
and composite indexes on `(user_id, created_at)` and `(created_at)`.

**Problem.** LLM spend is invisible until the bill arrives, and by then attribution is impossible.
The dependent controls — rate limiting and a monthly cap — cannot be *sized* without real usage
data first.

**Benefit.** One table serves three planned controls: the rows are the token log, per-user rate
limiting is an indexed `COUNT` over a window, and the spend cap is a `SUM(cost_usd)` for the month
(`models/llm_usage.py:12-22`). Per-completion granularity is necessary, not fussy: one query makes
two calls and a failover splits them across providers at different rates. Unpriced models write
**NULL**, never `0.0` (`config/pricing.py:56-70`), so "unknown price" stays distinguishable from
"free" when spend is summed. `record_usage` never raises (`usage_recorder.py:65-72`) — accounting
must not turn a good answer into a failed request.

**Tradeoff.** **The enforcement does not exist.** Rate limiting and the spend cap are unbuilt.
Today the ledger observes cost without constraining it — an authenticated user can call the agent
endpoint in a loop and the only effect is more rows. Prices in `config/pricing.py` are
operator-maintained constants that will silently drift from provider rates.

The roadmap contains a genuinely sharp piece of design reasoning here worth repeating in the
meeting: enforcement must live in a **route dependency, not inside `complete()`** — because
`intent_parser.py` catches broad exceptions and relabels them `INTENT_PARSE_ERROR`, which the
endpoint converts to a **200**. A budget error raised inside the pipeline would be silently
swallowed and returned as a clarifying question
(`docs/07_checklist/00_high_level_roadmap.md` §Cost Control, step 3). That is the kind of
second-order failure mode most teams find in production.

**Enterprise relevance.** No platform team will host an unmetered LLM endpoint. Per-user
attribution is the precondition for chargeback, and building the ledger before the caps is the
correct sequencing — you cannot choose a sensible budget number before you have measured anything.

---

## Decision 10 — Search scope returned as the citation **[IMPL]**, record-level provenance withheld **[PARTIAL]**

**Decision.** Every agent response includes `search_scope` — item, state, year range, and any
optional filters — alongside `record_count`, `provider`, `model`, and `request_id`. Scope is
captured *before* the query runs (`api/agent.py:141-149`), so it is returned even on the
zero-result and parse-failure paths.

**Problem.** "The AI says the average is $52.40" is not usable in an engineering context. The user
needs to know what was searched to judge whether the answer applies to their situation — and
crucially, to notice when the *system assumed something they did not ask for*, like the default
five-year window.

**Benefit.** Cheap, and disproportionately effective for trust. A user seeing
`state: "US", years: 2021–2026` immediately knows no geographic filter was applied and that the
window was assumed. It converts an opaque assertion into an inspectable query, and it makes the
system's assumptions falsifiable by the person best placed to catch them.

**Tradeoff — and this is the significant one.** Provenance is **scope-level, not record-level**.
The user cannot answer "which 47 records?" The original business requirement was explicit about
wanting source projects listed alongside the number
(`docs/00_overview/00_business_scope.md` §3: *"See the following projects for more details:
&lt;project name&gt;, &lt;project number&gt;, &lt;year&gt;, &lt;unit item cost&gt;"*).

The cause is an over-application of Decision 2. Raw records are correctly withheld from the
**LLM**; they are *also* withheld from the **authenticated human user**, who is authorized to see
them and for whom no third party is involved. Returning them alongside the answer would satisfy
the original requirement without weakening the LLM boundary at all — the two are independent
channels. See [Deliverable 9](09_architecture_risks.md), R-4.

**Enterprise relevance.** Determines whether output is usable in a deliverable. An estimator
cannot put a number in a bid they cannot source. Scope-level provenance supports *trust*;
record-level provenance supports *use*.

---

## Cross-cutting decisions worth one line each

| Decision | State | Note |
| --- | --- | --- |
| JWT HS256 + bcrypt, user re-loaded from DB per request | **[IMPL]** | Closest thing to revocation; no denylist, no refresh |
| `AppError` as single structured error type | **[IMPL]** | Consistent `{code, message}`; clean service→HTTP decoupling |
| Graceful degradation returns 200, not 4xx | **[IMPL]** | Right for UX; parse failures invisible to error-rate monitoring |
| Purge writes archive rows in the same transaction | **[IMPL]** | Fixed at `a532917`; was irreversible before |
| Binary `is_admin` instead of RBAC | **[IMPL]** | Adequate now; roadmap scopes roles/permissions |
| Postgres for budget state, explicitly not Redis | **[PLANNED]** | Documented reasoning: ledger must be durable, no Redis in CI |
| Snowflake OLAP read path | **[PLANNED]** | Design doc only; nothing in code |
| Aggregation in Python rather than SQL | **[IMPL]** | Portable and testable; transfers every matching row |
| `Float` rather than `Numeric` for `unit_price` | **[IMPL]** | Wrong type for currency; harmless today, undercuts the exactness claim |
