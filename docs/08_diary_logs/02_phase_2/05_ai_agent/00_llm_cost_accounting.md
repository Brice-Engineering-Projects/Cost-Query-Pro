---
title: LLM Cost Accounting — Token Usage Foundation
date: 2026-07-26
module: AI Agent / Cost Control
type: project
tags: [phase_2, ai_agent, llm, cost_control, sqlalchemy, alembic, mypy]
author: Brice Nelson
author_link: https://github.com/Brice-Engineering-Projects/Cost-Query-Pro
status: completed
---

## ✅ Session Summary

### 📦 Status

- ✅ `LLMProvider.complete()` widened to return usage metadata
- ✅ `llm_usage` table created (migration `c7a4e2b91d38`), verified both directions
- ✅ Per-completion token and cost accounting wired into `POST /api/v1/agent/query`
- ✅ Fixed a pre-existing cost-attribution bug in the fallback path
- 🚧 Rate limiting and monthly spend cap deferred to a follow-up session
- 🚫 Query result caching deferred — no invalidation trigger exists yet

Roadmap: Phase 2 → *Cost Control and Rate Limiting* → **Step 1 complete**.
Tests: 147 → 165 passing.

---

## 🎯 Why This Went First

The four cost-control roadmap items are not peers. Rate limiting and the spend
cap are both queries against data that did not exist yet, and the budget figure
in `LLM_MONTHLY_BUDGET_USD` cannot be chosen sensibly without a few weeks of
real usage to look at. Token logging also carried all of the cross-cutting
blast radius, so it had to land in one pass rather than be split.

**State lives in Postgres, not Redis.** `redis>=6.2.0` is declared in
`pyproject.toml` and `settings.redis_url` exists, but nothing imports the
client, there is no `docker-compose.yml` or `Dockerfile` anywhere in the repo,
and CI provisions only `postgres:16-alpine`. Adopting Redis would have meant a
CI service block, a lifespan-managed pool, and a local-dev fallback — all
before Phase 3 containerization exists. The budget ledger has to be durable
regardless, so one indexed table now serves three features: the rows are the
token log, a `COUNT` over a time window is the rate limit, and a
`SUM(cost_usd)` is the monthly spend.

---

## 🔧 What Changed

### 1. The provider Protocol was throwing usage away

`complete()` returned a bare `str`. Both implementations unwrapped the SDK
response and dropped it on the floor:

```python
# services/llm_provider.py — before
response = self._client.messages.create(**kwargs)
return next(b.text for b in response.content if b.type == "text")
```

`response.usage.input_tokens`, `response.usage.output_tokens`, and
`response.model` all went out of scope on that line. No amount of downstream
work could recover them — the widening was unavoidable.

The Protocol now returns a frozen `CompletionResult` carrying text, provider,
model, and both token counts. `MeteredProvider` wraps the configured provider
and appends one entry per call:

```python
@dataclass
class MeteredProvider:
    inner: LLMProvider
    calls: list[CompletionResult] = field(default_factory=list)
```

Accumulating on the instance is only safe because `get_llm_provider` builds a
**fresh provider per request** — no `lru_cache`, no singleton. That was already
true (and mildly wasteful, since it rebuilds both SDK clients every request),
but here it works in our favour: one instance never spans two requests, so
`provider.calls` is naturally request-scoped without any context-local
plumbing.

Blast radius: 3 provider classes, 2 services, 4 test files.

### 2. Cost attribution was silently wrong on fallback

Pre-existing bug, found only because we tried to bill against the field:

```python
# api/agent.py — before
def _resolve_model(provider_name: str) -> str:
    if provider_name == "openai":
        return settings.openai_model
    return settings.claude_model
```

`FallbackLLMProvider.name` is the constant string `"fallback"`, so this
returned `claude_model` for **every** fallback request — including ones where
Claude errored and GPT-4o actually produced the answer. The API response
reported Anthropic; a spend calculation built on it would have billed Anthropic
rates for OpenAI tokens.

Replaced with `_observed_provider()` / `_observed_model()`, which read the last
recorded completion rather than a configured name, falling back to the
configured value only when no call was made.

> ⚠️ **Any cost analysis over pre-fix data is unreliable.** The `provider` and
> `model` fields on historical agent responses are a guess about configuration,
> not an observation of what ran. There is no way to recover which requests
> actually failed over.

### 3. Two decisions that will look like mistakes later

**`cost_usd` is nullable, and unpriced models record NULL rather than `0.0`.**
Prices are hand-maintained constants in `config/pricing.py` — the SDKs return
token counts and never prices. When a model has no entry, coercing the cost to
zero would make an unpriced model indistinguishable from a free one, and the
monthly `SUM` would quietly under-report instead of visibly having a hole.
`estimate_cost_usd` returns `None` and logs once per model per process.

**Usage is recorded on the graceful-degradation return paths**, not just the
success path. An ambiguous question burns the intent-parse call; an empty
result set burns it too. Both return HTTP 200 with a friendly message, and both
cost money. Recording only on success would undercount exactly the number that
step 3 gates on.

`record_usage` also never raises — a failed accounting write is logged and
rolled back. Cost bookkeeping must not turn a successful answer into a failed
request.

### 4. Table shape

One row per **completion**, not per request. A single agent query makes two
calls, and a failover can split those two calls across two providers at
different rates. Per-request rows could not represent that.

```python
Index("ix_llm_usage_user_id_created_at", "user_id", "created_at")  # per-user COUNT + SUM
Index("ix_llm_usage_created_at", "created_at")                      # global COUNT + SUM
```

Both indexes exist ahead of the queries that need them, so steps 2 and 3 are
additive.

The `stage` column labels calls positionally beyond the two known pipeline
steps (`intent_parse`, `generate_response`). `services/agent_tools.py` and
`config/prompts.py` are fully implemented but currently dead code — if a
tool-use loop is ever wired up, the number of calls per request becomes
unbounded. Extra calls get `call_2`, `call_3`, … rather than being dropped.

Migration was hand-written rather than autogenerated: `SystemSetting`,
`ArchivedItem`, and `ArchivedProject` are absent from `models/__init__.py` and
therefore from `Base.metadata`, which makes `--autogenerate` liable to emit
spurious `DROP TABLE` statements for them.

---

## 🧠 Lessons

### A read-only `@property` silently breaks a Protocol

`MeteredProvider.name` was first written as a property delegating to
`self.inner.name`. Every test passed. mypy did not:

```
error: Argument 2 to "parse_intent" has incompatible type "MeteredProvider";
       expected "LLMProvider"
note:  Protocol member LLMProvider.name expected settable variable,
       got read-only attribute
```

`LLMProvider` declares `name: str` as a data member, which means a *settable*
attribute. A property satisfies `hasattr()` — so `isinstance()` against the
`runtime_checkable` Protocol still returns `True` — but fails static structural
typing. The runtime check and the static check disagree, and only the static
one is right.

Fixed with `name: str = field(init=False)` assigned in `__post_init__`. Worth
remembering: this provider layer is Protocol-based, so the next wrapper written
against it will hit the same wall.

### Quota errors cannot be raised from inside the pipeline

This is the constraint that shapes steps 2 and 3, so it is recorded here rather
than discovered again later.

`services/intent_parser.py:89` catches bare `Exception` and re-raises it as
`AppError("INTENT_PARSE_ERROR", ...)`. `api/agent.py` then catches that code and
returns **HTTP 200** with a clarifying question. So an exception raised anywhere
beneath `parse_intent` — including a spend-cap rejection raised inside
`complete()` — is converted into a cheerful "could you rephrase that?" and the
caller never learns the budget was exhausted.

**Rate limit and spend cap must be enforced in a route dependency that runs
before the handler body**, or that `except` must be narrowed first.

### The `TESTING=1` safety guard protects nothing

Unrelated to this work, found while verifying the migration downgrade path.
`db/session.py:28` refuses to run when `TESTING=1` unless the database name
ends in `_test`:

```python
is_test_db = str(u.database).endswith("_test")
```

The project's test database is `cost_query_pro_test_db`, which ends in `_db`.
The guard therefore rejects its own test database, and running any Alembic
command with `TESTING=1` set fails outright. It is harmless today only because
`tests/conftest.py` never sets the flag — which also means the check has never
actually guarded anything.

Either the suffix check should accept `_test_db`, or the guard should be
dropped as dead code. Not addressed here.

---

## 🔜 Follow-Up

| Item | Notes |
| --- | --- |
| Step 2 — rate limiting | `COUNT` over `llm_usage` in a route dependency; per-user and global. Indexes already in place. |
| Step 3 — monthly spend cap | `SUM(cost_usd)` against `settings.LLM_MONTHLY_BUDGET_USD`. Same dependency. Must run before `parse_intent` — see the swallow above. |
| Step 4 — result caching | Deferred. Cached cost answers go stale the moment new bid data lands, and the invalidation trigger is the ingestion pipeline, which is not implemented. |
| Verify pricing rates | `config/pricing.py` values are hand-maintained. `gpt-4o` in particular is the configured fallback and will get used — confirm against the provider pricing pages before trusting a spend figure. |
| `AppError` has no `headers` | A `429` cannot carry `Retry-After` or `X-RateLimit-*`. The sibling `HTTPException` handler forwards headers; the `AppError` handler at `main.py:84-89` does not. Step 2 will want this. |
