# Deliverable 7 — Extensibility

Assessed against the specific capabilities named in the review prompt. Effort ratings are
relative and assume the current codebase, not a rewrite.

---

## The boundaries that determine everything below

Four seams control how cheaply this system extends. Three help; one hurts.

| Seam | Effect |
| --- | --- |
| **`LLMProvider` Protocol** (`services/llm_provider.py:51`) — the only module importing an LLM SDK | **Helps.** Provider changes are one file |
| **`SearchParameters` / `CostSummary`** (`schemas/agent.py`) — the contract between every stage | **Helps.** Stages compose against types, not each other |
| **`run_ingestion(content: bytes, file_type: str)`** (`services/ingestion.py:110`) — parser dispatch over a normalized row list | **Helps.** New formats are one function |
| **`SearchParameters` as the *only* query vocabulary** | **Hurts.** Any question that does not fit item + state + years + unit + price range has no representation anywhere in the system |

That last one is the recurring theme: most "hard" extensions below are hard for the *same*
reason — the query model is a fixed five-field struct that the LLM must fill, and widening it
touches the prompt, the schema, the search function, and the scope output together.

---

## 1. Additional engineering data formats — **Easy**

**Why it is easy.** `run_ingestion()` dispatches on `file_type` to a parser that returns
`list[dict[str, Any]]`; every downstream stage — header normalization, validation, project
resolution, dedupe, lineage, quality issues — operates on that normalized shape. A new format is
one parser function plus a branch in `_detect_file_type()` (`api/ingest.py:23`).

**PDF specifically — the real work is not the parser.** `pdfplumber` and `pdfminer-six` are
already declared (`pyproject.toml:23,34`). The hard part is documented in the roadmap and is a
genuine architectural mismatch: bid tabs routinely carry `project_number` in a **page footer**
rather than a column. The current pipeline is strictly row-oriented — `_get_or_create_project()`
(`services/ingestion.py:62`) reads `row["project_number"]` and nothing carries document-level
context.

**[REC]** Introduce a document-context object (`{project_number, state, year, source_page}`)
produced by the parser and merged into each row before validation. Excel benefits identically —
the same footer convention appears in `.xlsx` exports. This is one structural change that unlocks
both formats and resolves an already-known Phase 1 gap.

**Boundary that helps:** parser dispatch.
**Boundary that hurts:** rows carry no document context.

---

## 2. Additional cost databases — **Moderate**

Adding a second source (RSMeans, a state DOT bid-tab feed, an internal historical archive)
requires a `source` dimension the schema does not have. `Project` has no provenance field beyond
`UploadHistory`, so cross-source queries cannot be filtered or weighted, and mixing an internal
bid tab with a published index would silently blend incomparable pricing.

**[REC]** Add `source` to `Project`, expose it in `SearchParameters` and `SearchScopeOut`, and
default to internal-only. The `SearchScopeOut` change matters as much as the query change — a
number blending two sources is only trustworthy if the response says so.

**Boundary that helps:** `UploadHistory` already models "where data came from" at the file level.
**Boundary that hurts:** no source dimension on the queryable entity.

---

## 3. Additional project metadata — **Easy to Moderate**

Adding columns to `Project` (owner agency, delivery method, county, bid date) is a migration plus
model change. The pipeline is indifferent.

Making them **queryable** is the moderate part: each new filter must be added to
`SearchParameters`, taught to the intent-parser prompt, implemented in `run_search`, and surfaced
in `SearchScopeOut`. Four coordinated edits per filter, and the prompt edit is the one that
degrades — every added field makes the extraction task harder and parse reliability worse.

**[REC]** This is where the **[WIRED-OFF]** tool-calling path in `services/agent_tools.py` earns
its keep. Tool schemas scale to many optional parameters far better than one monolithic
extraction prompt, because the model fills only what the question mentions. If metadata expansion
is on the roadmap, wiring the tools is the enabling change.

---

## 4. Alternative LLM providers — **Easy. The best-factored extension point in the system.**

`LLMProvider` is a `Protocol` with one method. `services/llm_provider.py` is the only module in
`src/` importing `anthropic` or `openai` — verified, no exceptions. Adding Bedrock, Azure OpenAI,
Vertex, or a self-hosted model is one class plus a branch in `build_provider()`.

`MeteredProvider` composes as a decorator, so metering comes free. `config/pricing.py` is a plain
dict; an unpriced model records **NULL** cost rather than corrupting spend totals.

**Genuine constraint:** the interface is the *intersection* of both SDKs —
`complete(messages, system, max_tokens)`. Tool use, streaming, prompt caching, and extended
thinking are not expressible. This is precisely why the tool-calling path is not wired in, and
widening the Protocol is a prerequisite for that work.

---

## 5. Embeddings / semantic search — **Moderate, and the highest-value extension available**

This directly addresses the weakest part of the system. Retrieval today is
`ILIKE '%{keyword}%'` (`services/item_search.py:34`) — lexical substring matching on a keyword an
LLM guessed. `"8-inch PVC water main"` will not match `8" PVC WM`, and cross-agency description
formatting varies enormously. Recall depends on the model happening to guess the source phrasing.

**Why the architecture accommodates it well:** `run_search()` has one job — turn
`SearchParameters` into `list[Item]`. A vector-similarity implementation satisfies the same
signature. `compute_summary`, the sanitizer, the endpoint, and the provenance output need no
changes at all. That is the payoff for having isolated retrieval behind a typed function.

**[REC]** Hybrid retrieval: pgvector over `item_description` embeddings unioned with the existing
`ILIKE` match, with structured filters (state, year, price) still applied deterministically in
SQL. Semantic recall, deterministic filtering — the split the architecture already believes in.

**Boundary that helps:** `run_search` is a clean, replaceable seam.
**Boundary that hurts:** none. This is the extension the architecture is best shaped for.

---

## 6. Cost forecasting / escalation analysis — **Hard**

Two structural obstacles:

1. **`CostSummary` has no temporal dimension.** It is five scalars over the whole result set.
   Trend analysis requires time-bucketed aggregates, which means a new schema — and every consumer
   of `CostSummary` (sanitizer, prompt builder, response model) changes with it.
2. **`Project.year` is the only time signal.** Bid *dates* are not captured, so the finest
   possible granularity is annual. For escalation analysis on volatile materials, annual buckets
   may not be sufficient.

**[REC]** Introduce `TimeSeriesSummary` as a *sibling* of `CostSummary`, not a replacement, with
its own sanitizer function. Add `bid_date` to `Project` for finer granularity. Keep the
whitelist-by-construction property — a new payload type needs its own hand-built serializer, and
that discipline is worth preserving even though it is more work.

---

## 7. Statistical analysis (percentiles, outliers, distributions) — **Easy**

`services/analytics.py` is 57 lines with no dependencies beyond stdlib. Adding percentiles,
stdev, IQR, or z-score outlier flagging is additive.

The real cost is the **sanitizer**, and that is by design: each new statistic must be explicitly
added to `_build_user_message()` (`response_generator.py:39`). Slightly tedious, and it is exactly
the property that prevents accidental data exposure. Do not "fix" it with a serializer.

**Worth noting:** the docs already anticipate percentiles, trend analysis, inflation adjustment,
regional comparison, and outlier detection (`docs/03_api/01_secure_ai_query_architecture.md`
§Step 5). Anticipated, not built.

---

## 8. ML models — **Hard, and mostly for the right reasons**

No feature store, no training pipeline, no model registry, no serving path. `Item` and `Project`
carry few features (description, unit, price, quantity, state, year).

But the architecture's *shape* is correct for it: an ML prediction is just another deterministic
computation whose output could be summarized and narrated by the same LLM layer. The
`compute → sanitize → narrate` pattern generalizes to `predict → sanitize → narrate` without
touching the boundary.

**[REC]** Do not add ML before semantic search and time-series aggregation. Both are
prerequisites in practice, and both deliver value on their own.

---

## 9. Regional cost comparisons — **Moderate**

`SearchParameters.state` is a single `str` constrained to exactly 2 characters
(`schemas/agent.py:28-34`), and `"US"` is overloaded as the "all states" sentinel
(`item_search.py:40`). Comparing FL against TX requires either two full pipeline runs or a
multi-value state field — and the sentinel collision has to be resolved first, because
`Optional[list[str]]` and a magic 2-char string do not coexist cleanly.

**[REC]** Replace the `"US"` sentinel with `Optional[list[str]] = None` (absent means all states).
This removes a latent bug — `"US"` is not a valid state code and a user typing it gets
all-states behavior — and unblocks comparison queries. Small change, disproportionate cleanup.

**Boundary that hurts:** a control value overloaded onto a domain field.

---

## 10. Time-based escalation analysis — **Hard**

Same constraints as §6, with the addition that `SearchParameters` expresses one contiguous year
range. "Compare 2019–2021 against 2023–2025" requires multiple ranges — a genuine schema change,
not a filter addition.

---

## 11. External engineering applications — **Easy**

The API is already well shaped for this: `/api/v1` prefix, OpenAPI auto-generated by FastAPI,
JWT bearer auth, consistent `{code, message}` errors, Pydantic-typed request/response models,
and a stable `request_id` correlation key.

**Constraints to disclose to any consumer:**
- No pagination on `/agent/query`; `/items/search` has `skip`/`limit` with a default of 100
- No rate limiting — an integrating system can exhaust the LLM budget
- No versioning policy beyond the `/v1` path segment
- CORS is dev-scoped (`main.py:79`)

See [Deliverable 8](08_integration_opportunities.md).

---

## 12. Internal enterprise systems (SSO, data warehouse, ERP) — **Moderate to Hard**

**SSO/OIDC — Moderate.** Auth0 settings already exist in `config/settings.py:98-102` (unused), so
the intent predates the current implementation. The obstacle is that `get_current_user` returns a
`DBUser` loaded by `username` from a local table (`core/security.py:91`) and roughly 20 route
handlers depend on that type. Swapping to OIDC means either provisioning local shadow users or
changing that return type everywhere. The dependency-injection structure makes this mechanical
rather than risky, but it is not a one-file change.

**Data warehouse — Moderate, already designed.**
`docs/01_architecture/02_cqp_snowflake_architecture.md` specifies a Postgres-writes /
Snowflake-reads split with secure views, role separation (`CQP_APP` read-only on views,
`CQP_ETL` on RAW/CORE), and resource monitors. **[PLANNED]** — no code exists, no Snowflake
dependency is declared. The design is sound and would specifically fix the unbounded-scan problem
in §Deliverable 9 R-1 by moving aggregation into SQL on an OLAP engine.

**ERP — Hard.** No integration surface, no scheduling, no outbound webhooks, no message bus.

---

## Summary

| Extension | Effort | Primary enabling or blocking boundary |
| --- | --- | --- |
| Alternative LLM providers | **Easy** | `LLMProvider` Protocol — the cleanest seam in the system |
| Additional statistics | **Easy** | `analytics.py` is dependency-free; sanitizer is deliberate friction |
| Additional data formats (CSV-like) | **Easy** | Parser dispatch over normalized rows |
| External API consumers | **Easy** | Versioned REST + OpenAPI + JWT already in place |
| Additional project metadata | **Easy→Mod** | Four coordinated edits per filter; prompt degrades |
| **Semantic search** | **Moderate** | `run_search` is a clean replaceable seam — **best value/effort** |
| PDF ingestion | **Moderate** | Parser dispatch helps; row-only context blocks footer extraction |
| Additional cost databases | **Moderate** | No `source` dimension on `Project` |
| Regional comparison | **Moderate** | Single-value `state` with overloaded `"US"` sentinel |
| SSO / OIDC | **Moderate** | `get_current_user` returns `DBUser` to ~20 handlers |
| Data warehouse | **Moderate** | Designed in detail; entirely unbuilt |
| Forecasting / escalation | **Hard** | `CostSummary` has no temporal dimension |
| ML models | **Hard** | No feature store or serving path; shape is right, substrate is not |
| ERP integration | **Hard** | No integration surface at all |

**The pattern worth naming in the meeting:** everything downstream of `SearchParameters` extends
cleanly, because the stages are typed, isolated, and side-effect-free. Everything that requires
*widening the query vocabulary itself* is expensive, because that vocabulary is simultaneously a
Pydantic schema, a prompt instruction, a SQL filter set, and a provenance output — and all four
must move together.

**If one extension is worth doing next: semantic retrieval.** It attacks the system's weakest
property (lexical recall on an LLM-guessed keyword), it fits behind an existing seam without
touching the security boundary, and it makes every other extension more valuable by improving the
quality of the record set everything else operates on.
