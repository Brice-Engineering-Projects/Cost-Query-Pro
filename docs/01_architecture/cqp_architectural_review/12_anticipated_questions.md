# Deliverable 12 — Questions You Should Be Prepared to Answer

**Method.** Written from the position of the *other* architect: someone competent, skeptical, and
looking for the seams. Ordered roughly by when they would surface in the conversation.

**Answers are deliberately omitted, as requested.** For each question: why an architect asks it,
what they are really probing, and where in the repository the honest answer lives. Several are
uncomfortable — those are the valuable ones.

---

## On the fundamental design choice

### Q1 — Why an LLM at all? A search form with three dropdowns solves 80% of this.

**Why they ask.** The sharpest possible opening, and a fair one. If the deterministic layer does
all the real work, the LLM is a natural-language veneer over `item`, `state`, and a year range —
a form with three fields. They are testing whether the AI is load-bearing or decorative.

**Really probing:** whether you can articulate the value of the LLM in terms of something the form
cannot do, or whether it was added because it is 2026.

**Where the honest answer lives:** `schemas/agent.py:8` — `SearchParameters` is genuinely five
fields. Also `docs/00_overview/00_business_scope.md` §3, where the original goal was phrased as a
conversation. The strongest ground is domain vocabulary — that "large diameter Jack and Bore"
resolves to a size convention an engineer knows and a dropdown cannot express. Note the irony
worth owning: `config/prompts.py` encodes exactly that vocabulary and **is not wired in**.

---

### Q2 — Why not just give the model read-only SQL access with a scoped role?

**Why they ask.** Text-to-SQL is the obvious alternative and it is more capable. A read-only role
on a view addresses the security objection directly. They want to know whether you rejected it for
reasons or by reflex.

**Really probing:** whether you understand the actual tradeoff — text-to-SQL buys expressiveness
and costs verifiability, and you deliberately bought the other one.

**Where it lives:** `services/item_search.py:31-48`. Strongest argument: a wrong query and a right
query return the same *shape* of answer, and nobody can tell them apart. Weakest point in your
position: the LLM already effectively controls the `WHERE` clause via the keyword, so the
difference is one of degree rather than kind. Be ready for that follow-up.

---

### Q3 — Why not semantic search or a vector database?

**Why they ask.** `ILIKE '%keyword%'` is the least sophisticated retrieval available, and item
descriptions are exactly the short, variably-formatted text embeddings handle well. They may
suspect this was never considered.

**Really probing:** whether you know your retrieval is the weak link.

**Where it lives:** `services/item_search.py:34`. The best answer concedes the point — this is the
highest-value unbuilt extension, `run_search` is a clean seam for it, and nothing downstream
changes. See [Deliverable 7](07_extensibility.md) §5.

---

### Q4 — You call this deterministic, but an LLM picks the search keyword. What is actually deterministic?

**Why they ask.** **The hardest question in the set, and the one to raise yourself before they do.**
The system's central claim is deterministic, auditable calculation. What is deterministic is the
arithmetic; which records the arithmetic runs over is chosen non-deterministically.

**Really probing:** intellectual honesty. How you answer this determines how much they believe of
everything else.

**Where it lives:** `intent_parser.py:80` → `item_search.py:34`. No `temperature` is set anywhere.
`SearchParameters` is not persisted. Two things genuinely help: `search_scope` makes the choice
*visible*, and a bad parse yields a wrong-scope answer rather than wrong math. See
[Deliverable 9](09_architecture_risks.md) R-2.

---

## On correctness and trust

### Q5 — Same question twice. Same answer?

**Why they ask.** The concrete form of Q4. Reproducibility is the property an engineering
organization needs before anything goes in a deliverable.

**Really probing:** whether you have measured this or merely reasoned about it.

**Where it lives:** the prose varies by design. The *number* varies only if the parsed keyword
varies — and nothing pins it. `llm_usage` records tokens per `request_id` but not parameters, so
an answer cannot be reproduced from server-side state after the fact.

---

### Q6 — How do I know the 47 records are the right 47?

**Why they ask.** Substring matching is both over- and under-inclusive. `%pipe%` catches pipe
fittings, pipe bollards, and pipe insulation. Missing records lower the count silently — there is
no error, just a different median.

**Really probing:** whether you have thought about recall and precision, or only about not
hallucinating.

**Where it lives:** `item_search.py:34`, `analytics.py:39`. `record_count` is returned, which lets
a user notice an implausible count. Nothing surfaces *what was matched*. This connects directly to
Q7.

---

### Q7 — Why can't I see the source records?

**Why they ask.** The stated goal was avoiding *"the AI says $52.40."* Scope-level provenance is
better than nothing and it still does not let an estimator source a number for a bid.

**Really probing:** whether the omission is a considered security decision or an oversight.

**Where it lives:** `schemas/agent.py:135` — `AgentQueryResponse` has no records field. The
business requirement (`docs/00_overview/00_business_scope.md` §3) explicitly asked for a source
project list. The honest answer is that it is an over-application: records are correctly withheld
from the **LLM** and *also*, unnecessarily, from the **authenticated user**. See
[Deliverable 9](09_architecture_risks.md) R-4.

---

### Q8 — What stops the model from writing a confident answer that misstates the statistics?

**Why they ask.** The second call gets five numbers and produces prose. Nothing checks the prose
against the numbers.

**Really probing:** whether "the LLM doesn't calculate" is an enforced property or only true of the
*inputs*.

**Where it lives:** `response_generator.py:18-36` — the constraints are prompt instructions,
returned verbatim with no post-check. The small-sample rule exists in `config/prompts.py`,
**which is imported by nothing**. A three-record answer reads as confidently as a three-hundred-record one.

---

## On failure modes

### Q9 — What happens when intent parsing fails?

**Why they ask.** Everything downstream depends on one LLM call succeeding. They want to know
whether failure is handled or merely caught.

**Really probing:** whether degradation is designed or incidental.

**Where it lives:** `intent_parser.py:87-100` → `api/agent.py:121-137`. This is a **strong** area:
200 with a clarifying question rather than a 4xx, and usage still recorded because the failed call
cost money. Two caveats worth volunteering: the handler catches bare `Exception`, so a genuine bug
becomes a user-facing clarifying question; and returning 200 means parse failures never appear in
HTTP error-rate monitoring.

---

### Q10 — How do you handle ambiguity — "compare PVC and ductile iron in Florida and Texas"?

**Why they ask.** Probing the expressiveness ceiling. `SearchParameters` holds one item and one
state.

**Really probing:** whether the system *knows* it cannot answer, or silently answers a narrower
question.

**Where it lives:** `schemas/agent.py:8` — single-valued `item` and `state`. The model must
collapse the question into one, and it will pick one interpretation without flagging that it did.
`search_scope` reveals what happened *after the fact*. Note that `services/agent_tools.py` is
exactly the unwired machinery that would fix this.

---

### Q11 — What happens if Anthropic is down mid-request?

**Why they ask.** Standard resilience probe, and it exposes whether failover was designed or
bolted on.

**Really probing:** whether the fallback is correct, and whether cost accounting survives it.

**Where it lives:** `llm_provider.py:157-195`. **Genuinely strong** — transparent failover with
usage attributed to the provider that actually served the call
(`api/agent.py:55-71`), so a failed-over request is not billed at Anthropic rates. Two weaknesses
to volunteer: all `anthropic.APIError` is caught including 4xx, so a malformed request fails
twice; and no timeout is set on either call.

---

## On data and ingestion

### Q12 — How do PDFs get normalized? Bid tabs are wildly inconsistent.

**Why they ask.** Anyone who has processed real bid tabs knows this is the hard part. They are
testing domain depth.

**Really probing:** whether PDF support is a bullet point or an understood problem.

**Where it lives:** **not implemented.** `pdfplumber` and `pdfminer-six` are declared
(`pyproject.toml:23,34`); `api/ingest.py:34-38` rejects PDF. The credibility recovery is the
roadmap's footer-`project_number` requirement — a real, specific, non-obvious problem, correctly
identified and not yet solved. Answering this well means being *ahead* of them on the problem
while being *behind* on the implementation, and saying both.

---

### Q13 — What happens on a partially bad file, and can I re-upload safely?

**Why they ask.** Operational reality. All-or-nothing ingestion is how most systems start and why
most ingestion becomes a support ticket.

**Really probing:** whether ingestion is self-service.

**Where it lives:** `services/ingestion.py:176-258` — **the strongest subsystem in the repository.**
Row-isolated failures, persisted `DataQualityIssue` rows, composite-key dedupe making re-upload
safe. One honest wrinkle to volunteer: a row with a malformed state silently becomes `"XX"`
(`ingestion.py:72-73`) with **no** quality record — the one place the pipeline degrades data
without saying so.

---

## On operations and scale

### Q14 — What is the cost per query, and what stops a user from running up a bill?

**Why they ask.** Any platform team asks this before hosting an LLM endpoint. Predictable cost is
a precondition for internal deployment.

**Really probing:** whether cost was designed for or discovered.

**Where it lives:** half a strong answer. `models/llm_usage.py` and `config/pricing.py` are
well-built — per-completion rows, correct NULL semantics for unpriced models, indexes sized for
the queries the controls will need. Exactly two calls per query makes the unit cost computable.
But **there is no rate limit and no cap** — enforcement is unbuilt. The roadmap's note about
enforcement belonging in a route dependency rather than inside `complete()` is worth repeating; it
shows the failure mode was thought through.

---

### Q15 — How does this behave at 10 million records? And what would you redesign today?

**Why they ask.** The closing question, usually asked as one. The first half is a scaling probe;
the second is an invitation to demonstrate judgment.

**Really probing:** whether you know where your own architecture breaks, and whether your
retrospective priorities are credible.

**Where it lives — scaling:** `item_search.py:50` has no `LIMIT`; `analytics.py:39` materializes
every row in Python; `ILIKE '%…%'` cannot use an index. The break is predictable and the mitigation
is known (SQL-side aggregation, trigram index, pagination). The Snowflake design
(`docs/01_architecture/02_cqp_snowflake_architecture.md`) addresses exactly this and is unbuilt.

**Where it lives — redesign:** the defensible list is aggregation in SQL rather than Python;
`Numeric` rather than `Float` for currency; a deterministic pre-parse in front of the LLM;
record-level provenance from day one; and either wiring in the tool-calling layer or deleting it.
The bad answer is a technology swap. The good answer names boundaries.

---

## The five to rehearse

Ranked by damage if answered poorly:

1. **Q4** — determinism. Raise it yourself, on slide 9, before they get there.
2. **Q7** — source records. The gap between the stated goal and the shipped response.
3. **Q1** — why an LLM. If this lands badly, the rest of the meeting is uphill.
4. **Q14** — cost control. Half built, and the built half is good. Be precise about which half.
5. **Q12** — PDF normalization. The domain answer is strong; the implementation answer is "not
   built." Give both, in that order.

**The pattern across all fifteen:** the questions that hurt are about the *input* side of the
LLM boundary — what gets selected, by whom, and how reproducibly. The output side is well defended
and they will spend little time there. Prepare accordingly.
