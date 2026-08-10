# Deliverable 10 — Architecture Presentation Outline

**Format:** 12 slides, ~18 minutes of presentation inside a 30-minute meeting.
**Audience:** one engineer building a potentially complementary internal application.
**Principle:** slides are sparse; the detail lives in the speaker notes. This is a conversation
with visual aids, not a deck.

**Structural change from the suggested outline.** The proposed structure ended with
*Limitations* at slide 11 and *Discussion* at slide 12. That ordering puts the weakest material
immediately before the part of the meeting that matters most. This version **moves limitations
to slide 9 (paired with the AI boundary, where they belong) and ends with integration**, so the
last thing said before discussion is the thing worth discussing. Slides 5 and 6 are also merged
because the deterministic/LLM split is the narrative spine and deserves a single sustained
treatment rather than two passes.

---

## Slide 1 — The problem, in one number

**Time:** 1.5 min

**Talking points**
- Historical unit costs live in bid tabs, PDFs, and spreadsheets across shared drives
- Estimators spend hours reconstructing what an organization already paid
- The obvious answer — "put an LLM on it" — fails for a specific reason: a hallucinated average
  lands in a bid, and it looks exactly like a correct one
- So the design question was never *"can AI answer cost questions?"* It was *"can AI answer them
  in a way an engineer is willing to sign?"*

**Visual:** left, a screenshot-style bid tab PDF fragment; right, a chat bubble reading *"The
average is $52.40."* with a red question mark. Nothing else.

**Speaker notes:** Open with the failure mode, not the product. The audience is an engineer who
has seen LLM demos; framing this as a *trust* problem rather than a *search* problem immediately
signals a different class of thinking. Do not describe the product yet.

---

## Slide 2 — Constraints that came from the domain, not the technology

**Time:** 2 min

**Talking points**
- **Consume data in its existing formats.** Excel, CSV, PDF. If engineers must restructure their
  workflow, the system never gets populated
- **Source data is dirty by default.** Merged cells, subtotal rows, notes in numeric columns
- **The number must be defensible.** It goes into a bid; "the AI said so" is not sourcing
- **Cost data is competitively sensitive.** Project numbers and contractor pricing cannot leave
  the environment

**Visual:** four constraint cards; beneath each, one arrow to the architectural consequence it
forced.

**Speaker notes:** This slide is what makes the rest non-obvious. Each constraint maps to a
specific decision: multi-format ingestion, partial-success ingestion, provenance in the response,
and the sanitized LLM boundary. If they only remember one slide, this is the one that shows the
architecture was *derived*, not selected.

On PDF: multi-format was designed in from inception — it is in the earliest scope documents and
`pdfplumber` is a declared dependency. **Say plainly that PDF is not yet implemented.** They will
check.

---

## Slide 3 — One principle

**Time:** 1.5 min

**Talking points**
- **The LLM translates and narrates. The application computes.**
- The LLM is treated as an untrusted external service *in both directions* — its output is
  validated before use, its input is whitelisted by construction
- Everything else in this deck follows from taking that literally

**Visual:** the sentence, large, on an otherwise empty slide. Below it, two small icons: an arrow
in labeled *validated*, an arrow out labeled *whitelisted*.

**Speaker notes:** Deliberately one idea. Pause here. This is the sentence you want repeated when
they describe your system to someone else. Resist adding a diagram.

---

## Slide 4 — System architecture

**Time:** 2.5 min

**Talking points**
- FastAPI modular monolith over PostgreSQL; ~3,800 lines of application code
- **Two independent lifecycles** that meet only at the database: ingestion never calls an LLM;
  querying never writes cost data
- One module in the entire codebase imports an LLM SDK
- The database holds four things: cost data, ingestion lineage, data-quality issues, and an LLM
  cost ledger

**Visual:** Diagram 1 from [Deliverable 2](02_architecture_diagram.md). Point at the single edge
to the external providers.

**Speaker notes:** Do not walk the boxes. Say the two-lifecycle thing, then put a finger on the
one arrow that reaches a third party and say: *that edge carries a question and five numbers. It
never carries a database row.* Move on. Depth here is a trap — the lifecycle slide does this work
better.

---

## Slide 5 — One question, end to end

**Time:** 3 min — **the most important slide**

**Talking points**
- *"What was the average unit cost for 8-inch PVC water main?"*
- LLM call 1 → `SearchParameters` → **validated against a Pydantic schema before anything acts on it**
- Deterministic search → deterministic aggregation → **`statistics.median()`, not a token prediction**
- Sanitize → LLM call 2 → prose
- Two LLM calls. Two DB reads. **No LLM stage touches the database; no database stage touches an LLM**

**Visual:** Diagram 2 from [Deliverable 2](02_architecture_diagram.md), purple LLM stages, green
deterministic stages.

**Speaker notes:** Slow down. This is where the architecture becomes concrete rather than
rhetorical. Three things to land:

1. The model never writes SQL — it fills a struct. Values reach the database as bound parameters,
   so injection is not mitigated, it is structurally absent.
2. The number is `statistics.median()`. Swapping Claude for GPT-4o changes the prose and cannot
   change the number.
3. Three of the five paths through this endpoint make **zero or one** LLM calls — empty results
   and parse failures never reach the second call. The expensive path is the exception.

If they interrupt here, let them. This is the conversation.

---

## Slide 6 — The boundary, and what actually crosses it

**Time:** 2 min

**Talking points**
- Outbound payload: the question, three scope fields, five numbers. That is the complete list
- Built as a **hand-written f-string, not a serializer** — you cannot leak a field that no line of
  code writes
- Adding a column to the `Item` model cannot change this payload
- Pinned by a test asserting eight forbidden field names never appear

**Visual:** Diagram 4 from [Deliverable 2](02_architecture_diagram.md) — the trust boundary — with
the nine-line sanitizer function printed beside it.

**Speaker notes:** The only slide where showing code is right, because the *brevity* is the
argument. Most teams claim "we sanitize before sending to the LLM"; almost none can put the
sanitizer on a slide. Whitelist-by-construction is a structural guarantee, not a procedural one —
that distinction is the point.

If enterprise deployment comes up: because `CostSummary` is already the only input to the
narration step, a no-egress mode that template-renders the answer and eliminates LLM call 2 is a
function swap, not a redesign. It is designed and not built.

---

## Slide 7 — Ingestion: partial success as a first-class outcome

**Time:** 2 min

**Talking points**
- A file is not accepted or rejected. 497 of 500 rows land; the operator learns which 3 failed
  and why
- Failures **persist** as `DataQualityIssue` rows keyed to the upload — so recurring problems from
  particular agencies become queryable
- Every cost record carries an FK to its source upload: file, user, timestamp
- Idempotent re-upload via a composite dedupe key
- CSV and Excel today. **PDF is specified, dependencies declared, not implemented**

**Visual:** Diagram 3 from [Deliverable 2](02_architecture_diagram.md), with the PDF node dashed.

**Speaker notes:** If they also ingest bid tabs, this is the slide where a real shared problem
surfaces — so leave room.

The most transferable thing here is a *requirement*, not code: bid tabs routinely place the
project number in a **page footer** rather than a column. Any row-oriented ingestion pipeline
fails on those files. Nobody anticipates this until they have processed real bid tabs. Offer it
freely — it is the most valuable thing in the meeting that costs nothing to give away.

---

## Slide 8 — Provenance: what the user gets besides a number

**Time:** 1.5 min

**Talking points**
- Every response carries `search_scope`: item, state, year range, filters, `record_count`
- Scope is captured **before the query runs**, so a zero-result answer still says what was looked for
- `provider` and `model` are **observed, not configured** — a failed-over request reports the truth
- `request_id` correlates the answer with server logs and the cost ledger
- The user can see that the five-year window was *assumed*, not requested

**Visual:** a real `AgentQueryResponse` JSON body, with `search_scope` highlighted.

**Speaker notes:** The goal was avoiding *"the AI says $52.40."* This achieves it partially and it
is worth being precise about which part.

Provenance is **scope-level, not record-level** — the user cannot yet ask "which 47 records?" The
cause is an over-application of the LLM rule: records are correctly withheld from the model and
*also* withheld from the authenticated human, who is entitled to them. Those are independent
channels. Fixing it is additive and does not touch the boundary. Say this before they ask; it
demonstrates you know where your own design is incomplete.

---

## Slide 9 — Where this architecture is weak

**Time:** 2 min — **the credibility slide**

**Talking points**
- **Determinism starts one stage late.** The arithmetic is exact; *which records get counted* is
  chosen by an LLM from free text, with no temperature set and parameters not persisted
- **Retrieval is lexical.** `ILIKE '%…%'` — `8" PVC WM` does not match `8-inch PVC water main`.
  Missed records lower the count silently
- **The endpoint spends money with no rate limit or cap.** The ledger is built; enforcement is not
- **Aggregation happens in Python with no `LIMIT`** — fine at thousands of rows, not at millions
- **Some built architecture is not wired in.** Tool-calling and the domain vocabulary prompt exist,
  are tested, and no route reaches them

**Visual:** five items, plain text, no styling. Deliberately unadorned.

**Speaker notes:** Present this without hedging. An architect who volunteers the weak points is
more credible than one who defends them after they are found — and every item here is findable in
ten minutes of reading the repo.

The first bullet is the real one and the honest formulation is: *given the parameters, the result
is exact and reproducible; given the question, it is not.* The mitigation is that the parameters
are returned to the user, so the non-determinism is visible rather than hidden. `temperature=0`
and persisting the parameters would close most of the remainder.

---

## Slide 10 — What extends cheaply, and what does not

**Time:** 1.5 min

**Talking points**
- **Cheap:** new LLM providers (one file), new statistics, new file formats, external API consumers
- **Moderate:** semantic search — `run_search` is a replaceable seam; nothing downstream changes
- **Expensive:** anything requiring a wider *query vocabulary* — `SearchParameters` is
  simultaneously a schema, a prompt instruction, a SQL filter set, and a provenance output, and
  all four move together
- Next highest-value extension: hybrid semantic + lexical retrieval

**Visual:** three columns — Easy / Moderate / Hard — with the enabling or blocking boundary named
under each.

**Speaker notes:** The generalizable lesson: everything downstream of the typed contract extends
cleanly; everything requiring the contract itself to widen is expensive. That is a useful thing
for them to hear whether or not we ever integrate.

---

## Slide 11 — Where two systems could meet

**Time:** 1.5 min

**Talking points**
- **LLM provider + metering library** — zero domain coupling; failover and per-call cost
  attribution. Useful to any internal application calling a model
- **The agent endpoint as a service** — JWT in, question in, answer plus provenance out
- **A shared cost-record schema** — probably worth more than any code reuse
- **Not recommended:** sharing auth code. Share an identity provider instead
- Integration has a permanent coordination cost; nothing here is proposed for its own sake

**Visual:** two application boxes with three candidate connectors between them, each labeled with
its prerequisite.

**Speaker notes:** Present as options, not a proposal. The genuinely strongest outcome is probably
schema convergence — agreeing on a cost-record shape and a project-identity key before two systems
diverge. That is cheap now, expensive later, and creates no release-cycle dependency.

---

## Slide 12 — Over to you

**Time:** remainder (~10 min, protected)

**Talking points**
- What are you building, and what does it need from cost data — read it, or own it?
- Do you ingest the same document types?
- Are you calling an LLM? If so, the provider layer and the sanitizer pattern transfer immediately
- Where do you think this design is wrong?

**Visual:** the four questions. Nothing else.

**Speaker notes:** Stop talking. This is the point of the meeting. The last question is genuine —
ask it and then be quiet. An outside architect looking at the intent-parsing seam or the
provenance gap will produce better critique in five minutes than another week of self-review.

---

## Timing

| Slides | Content | Time |
| --- | --- | --- |
| 1–3 | Problem, constraints, principle | 5 min |
| 4–6 | Architecture, lifecycle, boundary | 7.5 min |
| 7–8 | Ingestion, provenance | 3.5 min |
| 9 | Weaknesses | 2 min |
| 10–11 | Extensibility, integration | 3 min |
| 12 | Discussion | ~9 min |
| | **Total** | **~30 min** |

**If running long, cut slides 7 and 10** — ingestion detail and the extensibility matrix are the
most droppable, and both are better handled as answers to questions than as prepared material.
**Never cut slide 5 or slide 9.** One is the argument; the other is the credibility.

---

## Two rules for the room

1. **Do not open an editor.** Slide 6's nine-line sanitizer is the only code that belongs on a
   screen. If they want the repo, send it afterward.
2. **When something is not built, say "not built."** The roadmap marks the tool-calling layer and
   the domain prompt complete; they are not wired in. Anyone who reads `api/agent.py` sees that in
   two minutes, and one discovered overstatement discounts everything else said in the meeting.
