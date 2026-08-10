# Deliverable 8 — Integration Opportunities

**Framing.** Nothing is assumed about the other engineer's application beyond the premise that it
concerns historical construction cost data. This document identifies what in Cost Query Pro could
*reasonably* be shared, what could not, and — importantly — where sharing would be a bad idea.

**Bias applied deliberately:** integration has a permanent coordination cost. A component is only
listed as reusable if it would still be worth extracting after paying that cost.

---

## The reusability test

Three questions, applied to each component:

1. Does it depend on CQP's database schema?
2. Does it depend on CQP's HTTP/auth context?
3. Would a second consumer want the *same* behavior, or merely a similar one?

Components failing (1) or (2) need refactoring. Components failing (3) should be copied, not
shared — divergent requirements behind a shared interface produce a component that serves neither
consumer well.

---

## Tier 1 — Genuinely reusable with little or no change

### 1.1 The LLM provider abstraction — **the strongest candidate**

`services/llm_provider.py` (311 lines), `config/pricing.py`, `services/usage_recorder.py`,
`models/llm_usage.py`

**Why it is reusable.** It has zero coupling to construction cost data. `LLMProvider` is a
`Protocol` with one method; `CompletionResult` is a frozen dataclass of text, provider, model,
and token counts. Nothing in it knows what a bid tab is. It is the only module in `src/` importing
an LLM SDK, so extraction removes a whole dependency class from the host application.

**What a second application gets:** Claude-primary/OpenAI-fallback failover, a metering decorator
that composes without threading token counting through business logic, per-model USD pricing with
correct NULL semantics for unpriced models, and — the detail that matters — **attribution to the
provider that actually served the call**, so a failed-over request is not billed at the wrong
vendor's rates.

**The one coupling to break:** `usage_recorder.py` imports `models.llm_usage` and takes a
SQLAlchemy `Session`; `STAGES = ("intent_parse", "generate_response")` is CQP-specific pipeline
vocabulary. Both are shallow — accept a stage label as a parameter and define the persistence
target via a small protocol.

**Recommendation:** extract as an internal library. This is the clearest case in the repository:
any internal application calling an LLM needs failover and cost attribution, and neither is
interesting enough that two teams should build it twice.

---

### 1.2 The deterministic analytics function

`services/analytics.py` (57 lines)

Pure: `list[Item] → CostSummary`. Stdlib `statistics` only. No I/O, no settings, no session.

**The single coupling** is the `Item` type in the signature, used only for `item.unit_price`. A
one-line change to `list[float]` — or a `Protocol` with a `unit_price` attribute — makes it
universally reusable.

**Honest caveat:** it is 57 lines of stdlib calls. Sharing it is more about **agreeing on the
statistics** than about avoiding work. If both applications must report the same median for the
same records, a shared function is worth it. If not, copy it. The value here is *consistency*,
not *effort saved* — and it is worth being clear-eyed about which of those is being bought.

---

### 1.3 Query construction from structured parameters

`services/item_search.py` (59 lines)

`SearchParameters → list[Item]`. Clean signature, single JOIN, no HTTP awareness, parameterized
throughout.

**Coupling:** entirely to CQP's `Item`/`Project` models. Reusable only if the other application
adopts a compatible schema — which is a real possibility given both concern the same domain, and
is the most valuable form of alignment available if they do.

**Recommendation:** do not extract as code. Extract the **schema shape**
(`Project 1→N Item`, keyed on `project_number`, with `state`/`year` on the project) and the
`SearchParameters` contract. Two applications agreeing on a cost-record schema is worth
substantially more than either one reusing the other's query function.

---

## Tier 2 — Reusable as a service, not as a library

### 2.1 Ingestion and normalization — **the highest-value service candidate**

`services/ingestion.py` (258 lines), `models/upload_history.py`, `models/data_quality_issue.py`

**Why service-shaped rather than library-shaped:** ingestion writes directly to CQP's tables
(`services/ingestion.py:232-240`), so it cannot be imported without importing the schema. But as
a service it exposes exactly the right interface: **bytes in, normalized rows plus a structured
quality report out**.

**What is genuinely valuable here, and hard to rebuild:**

- Case-insensitive header normalization across CSV and Excel — mundane, and the source of endless
  bugs when reimplemented
- **Partial-success semantics.** A file is not accepted or rejected; 497 of 500 rows land and the
  operator learns precisely which 3 failed and why. For dirty engineering source data this is the
  correct model, and most teams build all-or-nothing first and regret it
- **Persisted data-quality issues** keyed to the upload, enabling pattern detection across
  agencies over time
- Idempotency via a composite dedupe key, so re-uploading a corrected file is safe
- Lineage: every record traceable to a file, a user, and a timestamp

**The domain knowledge is worth more than the code.** The roadmap's footer-based
`project_number` requirement — bid tabs routinely place the project number in a page footer
rather than a column — is the kind of thing only someone who has processed real bid tabulations
writes down. **It is not implemented.** If the other application ingests bid tabs, this
requirement is the single most valuable thing to hand over, and it costs nothing to share.

**Recommendation:** offer as a shared service *only if* both applications ingest the same document
types. Otherwise share the requirements document and the partial-success design pattern. The
second option is often the better trade — it transfers the expensive knowledge without creating
a coupling.

---

### 2.2 The secure query pipeline as a whole

`api/agent.py` + `intent_parser` + `item_search` + `analytics` + `response_generator`

**Reusable as an API, not as components.** `POST /api/v1/agent/query` is already a clean service
boundary: JWT in, one question in, answer plus provenance out. Another application could consume
it directly today.

**What it would need before that is reasonable:**
- Rate limiting and a spend cap (currently absent — an integrating system can exhaust the LLM
  budget unopposed)
- Service-to-service auth distinct from user JWTs
- A stated versioning policy beyond the `/v1` path segment
- Documented latency expectations (two sequential LLM calls, no streaming)

**Recommendation:** the most realistic near-term integration in this document. The other
application calls CQP's agent endpoint rather than rebuilding a query pipeline. It requires the
Priority-1 controls from [Deliverable 6](06_security_and_trust_model.md) §3 first — and that is a
reasonable trade, since those controls are needed regardless.

---

### 2.3 The "sanitized aggregate to LLM" pattern

`services/response_generator.py:39-61`

**Reusable as a pattern, not as code.** The function is nine lines of f-string specific to
`CostSummary`. What transfers is the *design rule*:

> Build LLM payloads by hand-writing a whitelist, never by serializing a model. You cannot leak
> a field that no line of code writes.

Combined with the paired test asserting forbidden terms are absent
(`tests/unit_tests/test_response_generator.py:150`), this is a small, teachable convention that
any internal AI application should adopt. It costs nothing to share and it is one of the few
things here that is genuinely better than the industry default.

---

## Tier 3 — Tightly coupled; do not extract

| Component | Why it stays |
| --- | --- |
| `api/agent.py` endpoint handler | Orchestration is CQP's five-step pipeline by definition. The *pattern* travels; the code does not |
| `services/intent_parser.py` | The prompt encodes CQP's exact `SearchParameters` schema. A different query vocabulary means a different prompt — the module is a thin wrapper around domain-specific prompt text |
| `config/prompts.py` | Construction-cost domain vocabulary. Valuable **as content** to any construction application, worthless to any other domain. **Note: currently imported by nothing** |
| `services/agent_tools.py` | Four tools bound to CQP's search and analytics. **[WIRED-OFF]** — no route reaches it. Do not offer as a capability |
| `models/*` | CQP's schema. Share the *shape*, not the classes |
| `api/items.py`, `api/projects.py` | Standard CRUD; no reuse value |
| `web/views/routes.py`, templates | Minimal UI; also contains an unauthenticated loopback call to its own API (`routes.py:22-24`) |
| `core/security.py` | Generic JWT/bcrypt helpers, but ~40 lines wrapping two libraries. Sharing costs more than copying |

---

## Authentication: a deliberate non-recommendation

The prompt lists authentication as a candidate. **It should not be shared as a component.**

`core/security.py` is roughly 40 lines wrapping `PyJWT` and `bcrypt`, with a `DBUser` return type
that ~20 CQP route handlers depend on. Extracting it means either both applications adopt CQP's
user table, or the shared piece shrinks to "call `jwt.decode`" — which is not worth a dependency.

**What *should* be shared is the identity provider, not the code.** If both applications will run
internally, the correct convergence is a common OIDC/SSO provider issuing tokens both accept.
That is a genuine integration; sharing a JWT helper is not. Auth0 settings already sit unused in
`config/settings.py:98-102`, so the intent exists — it is a good thing to discover a shared need
for in the meeting.

---

## Integration shapes, ranked by realism

| Shape | Realism | Prerequisites |
| --- | --- | --- |
| **1. Share the LLM provider + metering library** | **High** | Decouple `usage_recorder` from CQP's model; parameterize stage labels |
| **2. Other app calls CQP's `/agent/query`** | **High** | Rate limiting, spend cap, service auth, versioning policy |
| **3. Converge on a shared cost-record schema** | **High** | Agreement on `Project`/`Item` shape and the `project_number` key. Highest long-term value, lowest technical risk |
| **4. Share ingestion as a service** | **Medium** | Only if both ingest the same document types |
| **5. Share the sanitizer pattern + boundary test** | **High** | None. Free to adopt |
| **6. Common OIDC/SSO provider** | **Medium** | Organizational, not technical |
| **7. CQP as the cost-data system of record with a read API** | **Medium** | Pagination, source dimension, record-level provenance |
| **8. Share `analytics.py`** | **Low value** | Trivial to copy; share only to guarantee identical statistics |
| **9. Share auth code** | **Not recommended** | Share the IdP instead |

---

## The three questions that should decide this in the meeting

Rather than proposing integration, establish whether the premise holds:

1. **Does the other application need to *read* historical cost data, or to *own* it?**
   Reading → CQP is a service. Owning → the conversation is about schema convergence, and the
   real risk is two divergent systems of record for the same data.

2. **Does it ingest the same document types?**
   If yes, ingestion is genuinely shared work and the footer-`project_number` problem is worth
   solving once. If no, ingestion should not be shared at any price.

3. **Does it call an LLM?**
   If yes, the provider abstraction and the sanitizer pattern transfer immediately and cheaply,
   independent of every other answer. This is the one recommendation that survives all three
   branches.

**And the thing worth saying plainly:** the strongest integration outcome available here is
probably not code reuse at all. It is **agreeing on a common cost-record schema and a common key
for project identity** before two systems diverge. That is cheap now and expensive later, and it
does not require either team to depend on the other's release cycle.
