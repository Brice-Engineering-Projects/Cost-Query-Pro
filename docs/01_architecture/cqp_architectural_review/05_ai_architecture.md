# Deliverable 5 — AI Architecture

---

## 1. The responsibility split, precisely

### What the LLM does — the complete list

Two calls. Nothing else in the system invokes a model.

| Call | Module | Receives | Produces | Consequence of being wrong |
| --- | --- | --- | --- | --- |
| 1 — Intent parse | `services/intent_parser.py:55` | Static system prompt + user's raw question | JSON → `SearchParameters` | **Wrong records get counted.** Silent. |
| 2 — Narrate | `services/response_generator.py:64` | Static system prompt + question + 3 scope fields + 5 numbers | Prose | Misleading wording around correct numbers |

That is the entire AI surface: **interpret a question into filters** and **describe five numbers
in English**.

### What deterministic code does

| Responsibility | Module |
| --- | --- |
| Authentication and authorization | `core/security.py` |
| Query construction (SQLAlchemy, parameterized) | `services/item_search.py:31-48` |
| All database access | `services/item_search.py`, `agent_tools.py` |
| All arithmetic — count, median, mean, min, max | `services/analytics.py:39-47` |
| Payload sanitization | `services/response_generator.py:39-61` |
| Output schema validation of model output | `schemas/agent.py:8` |
| Error taxonomy and HTTP mapping | `core/errors.py`, `main.py:86-115` |
| Graceful degradation decisions | `api/agent.py:121-174` |
| Provider selection and failover | `services/llm_provider.py:157-195` |
| Cost accounting | `services/usage_recorder.py`, `config/pricing.py` |
| Provenance assembly | `api/agent.py:141-149` |

### The three properties that make the split real rather than rhetorical

1. **`services/intent_parser.py` has no `Session` parameter.** It structurally cannot reach the
   database. This is enforced by the function signature, not by discipline.
2. **`services/item_search.py` and `services/analytics.py` import no LLM SDK.** Verified: the only
   module importing `anthropic` or `openai` anywhere in `src/` is `services/llm_provider.py`.
3. **The sanitizer is an f-string, not a serializer.** You cannot leak a field by adding a column
   to a model, because no code here reads a model.

---

## 2. Is the separation appropriate? Yes — for what it covers

The boundary is correctly placed and genuinely enforced *for the downstream half*. Specifically:

- The number in the answer cannot be a hallucination. It is `statistics.median()` over rows.
- No project name, project number, contractor, or per-record price can reach a third-party API.
- SQL injection via model output is structurally impossible — values are bound parameters, and
  the model never emits syntax.
- Changing providers cannot change a computed result.

That is a stronger set of guarantees than most production LLM integrations can claim, and the
architecture deserves credit for it.

---

## 3. Where the LLM has too much responsibility

### 3.1 The intent parser is a single point of non-determinism at the front of a deterministic pipeline — **the central finding**

The system's claim is deterministic, auditable calculation. What is actually deterministic is the
**arithmetic**. What is *not* deterministic is **which records the arithmetic runs over** — and
that is chosen entirely by an LLM, from an unconstrained natural-language string, with no
temperature setting anywhere in the codebase.

Concretely: `params.item` becomes `ILIKE '%{params.item}%'` (`item_search.py:34`) and is the sole
determinant of the result set. Ask the same question twice and the model may return
`"8-inch PVC water main"`, `"8 inch PVC"`, or `"PVC water main"`. Those are three different
queries returning three different record sets and three different medians — each computed
perfectly deterministically.

**The precise formulation:** *given the parameters*, the result is exact and reproducible. *Given
the question*, it is not. The determinism guarantee is real but it starts one stage later than
the marketing suggests, and an architect reviewing this will find that seam immediately.

Two things make this materially better than it sounds, and both should be said in the same breath:

- **The parameters are returned to the user.** `search_scope` makes the non-determinism *visible*
  rather than hidden. A user who gets a surprising number can see the keyword that produced it.
  That is a genuinely good mitigation, and most systems with this problem do not have it.
- **The blast radius is bounded.** A bad parse produces a *wrong-scope* answer, never a *wrong-math*
  answer, and never a data leak.

**What would close it further** (all **[REC]**):
- Set `temperature=0` on the parse call. Currently unset — behavior depends on each provider's
  default. Cheapest possible improvement.
- Persist `(question → SearchParameters)` per `request_id`. The pieces exist — the ledger already
  keys on `request_id` — but parameters are not stored, so an answer cannot be reproduced from
  server-side state after the fact. This is the gap between *visible* provenance and *auditable*
  provenance.
- Add a deterministic pre-parse for the ~70% of questions that are pattern-matchable (a state
  name, a 4-digit year or "last N years", a unit token), and call the LLM only for the residue.
  Cuts cost, latency, and variance simultaneously.
- Return candidate normalizations when a keyword matches several distinct item families, rather
  than silently picking one.

### 3.2 The narration call's constraints are advisory, not enforced

The system prompt (`response_generator.py:18-36`) instructs the model to state the record count,
quote median and average, note the range, mention the filters, and never invent data. **Nothing
verifies compliance.** The model's text is returned to the user verbatim
(`api/agent.py:177-195`) with no post-check.

Failure modes that are possible today:
- Omitting the record count — removing the caveat that makes a 3-record answer honest.
- Rounding or restating a number inconsistently with `record_count` in the same JSON response.
- Adding unsupported interpretation ("prices have been rising") from five summary statistics that
  contain no temporal information at all.

`config/prompts.py` contains a rule for exactly this — *"If record count is low (< 5), caution
the user that the sample is small"* — but **that file is imported by nothing**. The live prompt
does not include it.

**[REC]** A deterministic post-check is cheap and high-value: assert the answer string contains
`record_count`; assert every currency figure in the prose appears in the `CostSummary`; append a
system-generated small-sample warning below the LLM text when `record_count < 5` rather than
asking the model to remember. The last one converts a prompt instruction into a guarantee for
roughly ten lines of code.

### 3.3 The user's question is passed verbatim into both calls

`intent_parser.py:78` and `response_generator.py:50` both interpolate the raw question.

The blast radius is genuinely small, and this should be stated confidently rather than
defensively: there are no tools, no SQL generation, no database access from either call, and the
sanitizer is positional so injected text cannot introduce fields. The realistic attacks are
**self-directed** — a user manipulating the answer *they themselves* receive, or steering the
parser toward a scope that produces a flattering number while `search_scope` still reports the
real filters.

It becomes a genuine concern the moment either of two currently-planned things lands: tool-calling
(the code is written), or any feature where one user's question influences another user's output
(shared history, cached answers, saved queries).

**[REC]** Delimit the question inside the prompt and instruct the model to treat it as data;
log the parsed `SearchParameters` for anomaly review. Both are small and both age well.

### 3.4 Two LLM calls where one and a half would do

Every query pays for two round trips. The first is a structured-extraction task that a smaller,
cheaper model handles well — and much of it is pattern-matchable without a model at all.

**[REC]** Route call 1 to a cheaper model (the provider abstraction already supports per-call
model selection at the constructor level; `config/pricing.py` already prices Haiku and
`gpt-4o-mini`). Combined with a deterministic pre-parse, this is the largest available cost and
latency win, and it *increases* determinism rather than trading against it.

---

## 4. Where deterministic control is stronger than expected

Worth saying out loud, because these are easy to undersell:

- **Empty result sets never reach an LLM.** `compute_summary` raises `NO_RESULTS`; the endpoint
  returns a template message with full scope (`api/agent.py:155-172`). No second call, so no
  opportunity to hallucinate about nothing — and it is also the cheapest possible path.
- **Parse failure never reaches an LLM.** The clarifying question is a Python constant
  (`api/agent.py:36-40`), not model output.
- **Provider and model in the response are observed, not configured** (`api/agent.py:55-71`), so
  a failed-over request reports the truth.
- **Usage is recorded on all four exit paths**, including both degradation returns.
- **Aggregation is stdlib.** `statistics.median()` — no dependency, no service, no version drift.

Three of the five paths through the agent endpoint involve **zero or one** LLM calls. The
expensive path is the exception, not the default. That is good design.

---

## 5. The unwired AI architecture

Two substantial pieces of AI architecture exist, are tested, and are unreachable:

**`services/agent_tools.py`** — 319 lines. Four Anthropic-format tool definitions with backend
handlers, all returning Pydantic aggregates rather than records (`handle_project_lookup` returns
counts and state lists, never project rows). Dispatcher raises `UNKNOWN_TOOL` on unrecognized
names. 27 tests. **No route imports it.**

**`config/prompts.py`** — the domain vocabulary prompt: pipe types (DIP, PVC, HDPE, RCP, CIPP),
diameter conventions ("large" = 18–36"), unit abbreviations, installation methods, cost drivers,
plus the small-sample rule. **Imported by nothing.** `settings.agent_prompt_version` is defined
and never read.

**Why this matters for the meeting.** The roadmap marks both complete
(`docs/07_checklist/00_high_level_roadmap.md` §Agent Architecture and Tools, all `[x]`). If they
are presented as operating and the other engineer opens `api/agent.py`, the credibility cost
exceeds any benefit. Present them as *designed, built, and staged behind the current pipeline* —
which is accurate, still impressive, and is genuinely the answer to "how would you handle
multi-part questions?"

**The domain prompt is the more valuable of the two and the cheaper to activate.** Merging its
vocabulary into the intent parser's system prompt would directly improve the weakest part of the
system (§3.1): a model that knows `DIP` means ductile iron pipe and that "large diameter" means
18–36 inches produces materially better keywords than one working from general knowledge. That is
a small change against the highest-leverage defect.

---

## 6. Scorecard

| Dimension | Assessment |
| --- | --- |
| Numerical correctness | **Strong.** LLM cannot produce a number the user sees |
| Data-leak prevention | **Strong.** Whitelist-by-construction, test-pinned |
| Injection resistance (SQL) | **Strong.** Structurally impossible |
| Cost predictability | **Strong.** Exactly two calls; ledger per completion |
| Provider independence | **Strong.** One file; observed-model attribution |
| Graceful degradation | **Strong.** Three of five paths avoid the expensive call |
| Prompt-injection resistance | **Adequate today.** Small blast radius; degrades if tools land |
| Output conformance | **Weak.** Instructions advisory; no post-check |
| Scope reproducibility | **Weak.** LLM picks the keyword; no temp=0, params not persisted |
| Retrieval quality | **Weak.** Lexical substring match; no semantic fallback |

**Summary judgment.** The separation is correctly conceived and honestly implemented on the
output side. The exposure is concentrated at the **input** side, where a single unconstrained LLM
call decides what gets measured. That is the right thing to lead with when the other architect
asks where this design is weakest — naming it first is more persuasive than defending it after
they find it.
