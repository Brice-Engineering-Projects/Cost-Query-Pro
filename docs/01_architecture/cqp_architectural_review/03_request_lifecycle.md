# Deliverable 3 — Request Lifecycle

**Traced question:** *"What was the average unit cost for 8-inch PVC water main?"*

Deliberately chosen because it exercises the interesting edges: it names an item but **no state
and no year range**, so it forces the intent parser to invent scope — which is exactly where
the architecture's determinism guarantee gets tested.

---

## Stage 0 — API boundary

`POST /api/v1/agent/query`
Router registered at `main.py:122`; handler at `api/agent.py:78`.

```json
{ "question": "What was the average unit cost for 8-inch PVC water main?" }
```

Pydantic validates against `AgentQueryRequest` (`schemas/agent.py:64`) before the handler body
executes: `question` is required, 1–2000 characters. A caller-supplied `request_id` is optional.

**Architectural note.** The endpoint takes one field. There is no `state`, `year`, or `limit`
parameter — the natural-language string is the entire interface. Every structuring decision is
therefore delegated to the LLM. This is the source of both the product's ease of use and its
reproducibility weakness.

---

## Stage 1 — Authentication

`Depends(get_current_user)` (`core/security.py:75`) resolves before the handler body.

Decodes the HS256 JWT with `settings.secret_key`, extracts `sub`, and **re-loads the user row
from the database** on every request. That last part matters: a deleted user's still-valid
token fails at the DB lookup, which is the closest thing to revocation the system has. There is
no token denylist and no refresh flow.

Failure → `AppError("INVALID_CREDENTIALS", …, 401)` → JSON `{code, message}` via the handler at
`main.py:86`.

**Not present:** rate limiting, per-user quota, spend cap. This endpoint spends real money on
every call and an authenticated user may call it in an unbounded loop. See
[Deliverable 6](06_security_and_trust_model.md), §3.

---

## Stage 2 — Correlation identity

```python
request_id = body.request_id or str(uuid4())
```

Assigned first (`api/agent.py:98`) so it can tag every log line and every ledger row on all four
exit paths. Returned to the caller. This is the join key between the answer a user is looking at
and the server-side record of how it was produced — the minimum viable primitive for
after-the-fact investigation.

---

## Stage 3 — Intent parsing (LLM call 1 of 2)

`services/intent_parser.py:55`

**What leaves the building:** a system prompt (static, `intent_parser.py:19-43`) and the user's
raw question. No database content. This is verifiable by inspection — the function signature
takes `question: str` and a provider, and has no `Session` parameter. The module cannot reach
the database.

**What comes back** is expected to be bare JSON. The implementation is realistic about model
behavior: `_strip_code_fences()` (`intent_parser.py:46`) removes markdown fencing before parsing,
because models add it regardless of instructions.

**The validation gate:**

```python
params = SearchParameters.model_validate_json(cleaned)
```

`SearchParameters` (`schemas/agent.py:8`) is the security-relevant type in the system. It
enforces `intent` as the `Literal["cost_search"]`, `item` at 1–500 chars, `state` at exactly 2
chars, years in 1900–2100, non-negative prices, and `extra="ignore"` so unexpected model output
is dropped rather than propagated. Anything that fails becomes
`AppError("INTENT_PARSE_ERROR", …, 400)`.

**For our question, the model is expected to return approximately:**

```json
{ "intent": "cost_search", "item": "8-inch PVC water main",
  "state": "US", "year_start": 2021, "year_end": 2026 }
```

Two prompt-encoded defaults fired here, and both deserve mention in the meeting:

- **`"US"` as a sentinel for "no state given."** It satisfies the 2-character constraint and is
  special-cased downstream at `item_search.py:40`. Functional, but it overloads a domain field
  with a control value — an `Optional[str] = None` would express the same thing without the
  collision.
- **A five-year default window**, computed by the *model* from `_CURRENT_YEAR = 2026`, a constant
  hardcoded at `intent_parser.py:17`. In 2027 this silently produces the wrong window with no
  error. Small bug; large illustration of the general risk of pushing policy into prompt text.

**Failure path — genuinely good behavior.** An unparseable response returns **HTTP 200** with a
canned clarifying question (`api/agent.py:36-40, 124-137`), not a 4xx. The design position is
that "I couldn't understand you" is a conversational outcome, not a protocol error. Usage is
recorded on this path too, because the failed call still cost money.

---

## Stage 4 — Scope capture

`api/agent.py:141-149`

`SearchScopeOut` is built from `params` **before the query executes**. Consequence: the
provenance returned to the user describes the *intended* search even when it matches nothing,
so a zero-result answer still tells the user what was looked for. Cheap decision, disproportionate
trust payoff.

---

## Stage 5 — Query construction and database interaction

`services/item_search.py:17`

```python
query = (db.query(Item)
    .join(Item.project)
    .filter(Item.item_description.ilike(f"%{params.item}%"))
    .filter(Project.year >= params.year_start)
    .filter(Project.year <= params.year_end))
if params.state != "US":
    query = query.filter(Project.state == params.state)
```

**No SQL is ever generated by the LLM.** SQLAlchemy builds a parameterized statement from
validated fields; the model's output reaches the database only as a *bound parameter value*,
never as syntax. Classical SQL injection is structurally impossible here, and that is a
consequence of the architecture rather than of input sanitization.

Three properties worth naming honestly:

1. **`ILIKE '%…%'` is a substring scan.** No index on `item_description` can serve a leading
   wildcard. This is fine at current volume and is the first thing that breaks at scale. The
   roadmap already scopes a trigram index (§Search Performance).
2. **There is no `LIMIT`.** Every matching row is materialized as an ORM object in Python.
   A question like *"what does pipe cost?"* loads the entire pipe corpus into memory.
3. **Matching is lexical, not semantic.** `"8-inch PVC water main"` will not match a record
   described as `8" PVC WM` — a formatting difference that is completely normal across agencies.
   Recall depends on the model happening to guess the phrasing used in the source documents.

---

## Stage 6 — Aggregation

`services/analytics.py:18`

```python
prices = [float(item.unit_price) for item in items]
CostSummary(record_count=len(prices),
            median_price=stats_lib.median(prices),
            average_price=stats_lib.mean(prices),
            minimum_price=min(prices), maximum_price=max(prices))
```

**This is the architectural centerpiece.** The number the user reads is produced by
`statistics.median()` over concrete database values. It is exact, repeatable given the same
inputs, and independent of model, temperature, provider, or prompt version. Swapping Claude for
GPT-4o changes the prose and cannot change the number.

Two caveats to hold in reserve:

- Aggregation runs in **Python, not SQL** — the tradeoff for portability and testability is
  transferring every matching row over the wire.
- `Item.unit_price` is a **`Float`** (`models/item.py:35`), i.e. binary floating point, for a
  currency value. `Decimal`/`NUMERIC` is the correct type for money. It does not matter at
  today's precision and it undercuts the "exact, auditable arithmetic" claim if someone checks.

**Empty result** raises `AppError("NO_RESULTS", …, 404)`, which the endpoint catches
(`api/agent.py:155-172`) and converts to a **200** with a helpful message and the full scope. No
second LLM call is made — a real cost optimization, since the expensive call is the one that
never happens.

---

## Stage 7 — Sanitization and prompt construction

`services/response_generator.py:39-61`

This is the trust boundary, and its implementation is the reason the boundary is credible:

```python
return (f"User question: {question}\n\n"
        f"Search scope:\n  Item: {params.item}\n  State: {state_label}\n"
        f"  Years: {params.year_start}–{params.year_end}\n\n"
        f"Aggregate statistics ({summary.record_count} records):\n"
        f"  Median unit price:  ${summary.median_price:,.2f}\n"
        …)
```

**It is a hand-written f-string, not a serializer.** No `model_dump()`, no ORM object, no dict
comprehension over a record. You cannot leak a field by adding a column to `Item`, because
nothing here iterates over `Item`. Whitelisting-by-construction — a stronger guarantee than any
filtering approach, and the single most defensible security decision in the codebase.

The paired system prompt (`response_generator.py:18-36`) instructs the model to state record
count, quote median and average, note the range, mention the filters, and never invent data or
reference project names. Those instructions are **advisory**, not enforced — see
[Deliverable 5](05_ai_architecture.md), §5.

Verified by `tests/unit_tests/test_response_generator.py:150` (`test_security_boundary_no_raw_project_data`),
which asserts eight forbidden field names are absent from the outbound payload.

---

## Stage 8 — Response generation (LLM call 2 of 2)

`services/response_generator.py:64`

The model receives the sanitized string, the system prompt, and `max_tokens=1024`. It returns
prose. `MeteredProvider.complete()` (`llm_provider.py:226`) appends a `CompletionResult` —
text, provider, model, input tokens, output tokens — to the per-request `calls` list.

**Failover:** if Claude raises `anthropic.APIError`, `FallbackLLMProvider` (`llm_provider.py:157`)
transparently retries against OpenAI. The recorded `CompletionResult` names *the provider that
actually served the call*, so a failed-over request is not billed at Anthropic rates. The commit
history shows this was a real bug that was found and fixed
(`docs/07_checklist/00_high_level_roadmap.md` §Cost Control, step 1).

---

## Stage 9 — Response and provenance

```json
{
  "answer": "Based on 47 records for 8-inch PVC water main across all states (2021–2026), the median unit price was $52.40 per unit and the average was $54.18. Prices ranged from $38.00 to $79.50…",
  "record_count": 47,
  "search_scope": { "item": "8-inch PVC water main", "state": "US",
                    "year_start": 2021, "year_end": 2026,
                    "unit": null, "price_min": null, "price_max": null },
  "provider": "claude",
  "model": "claude-sonnet-4-6",
  "request_id": "3f2a…"
}
```

**What this achieves.** The user is not asked to trust a sentence. They can see that 47 records
were used, that no state filter was applied, that the window was 2021–2026 — and can immediately
tell that the five-year window was *assumed*, not requested. That is the difference between
"the AI says $52.40" and "a specific, inspectable query returned $52.40."

**What this does not achieve, and should.** The response does not name a single source project.
The user cannot answer "which 47 records?" — the original business requirement
(`docs/00_overview/00_business_scope.md` §3) explicitly asked for a source-project listing
alongside the number. Provenance here is *scope-level*, not *record-level*. The information is
in the database, the user is authenticated and authorized to see it, and it never needs to touch
the LLM to be returned. See [Deliverable 9](09_architecture_risks.md), R-4.

`provider` and `model` are read from the *observed* last completion
(`api/agent.py:55-71`), not from configuration — so the response tells the truth after a
failover.

---

## Stage 10 — Cost ledger

`services/usage_recorder.py:24`

One `llm_usage` row per completion — here, two rows sharing `request_id`, staged
`intent_parse` and `generate_response`, each with provider, model, token counts, and a
`cost_usd` computed from `config/pricing.py`. Unpriced models write **NULL**, never `0.0`.

The write is wrapped in try/except and swallows its own failures
(`usage_recorder.py:65-72`) — a ledger failure must not convert a successful answer into a 500.

---

## Full-path summary

| # | Stage | Module | LLM? | DB? |
| --- | --- | --- | :-: | :-: |
| 0 | API boundary + schema validation | `api/agent.py:78` | — | — |
| 1 | Authentication | `core/security.py:75` | — | read |
| 2 | Correlation ID | `api/agent.py:98` | — | — |
| 3 | Intent parsing | `services/intent_parser.py:55` | **yes** | — |
| 4 | Scope capture | `api/agent.py:141` | — | — |
| 5 | Query construction + execution | `services/item_search.py:17` | — | read |
| 6 | Aggregation | `services/analytics.py:18` | — | — |
| 7 | Sanitization + prompt build | `services/response_generator.py:39` | — | — |
| 8 | Response generation | `services/response_generator.py:64` | **yes** | — |
| 9 | Response assembly | `api/agent.py:188` | — | — |
| 10 | Cost ledger | `services/usage_recorder.py:24` | — | write |

**Two LLM calls. Two database reads. One database write. No LLM stage touches the database, and
no database stage touches an LLM.** That separation is the architecture, and tracing this one
request is the most convincing way to demonstrate it.
