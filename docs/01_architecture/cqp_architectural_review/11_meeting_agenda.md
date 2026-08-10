# Deliverable 11 — Meeting Agenda

**Duration:** 30 minutes
**Format:** technical discussion between two engineers. Not a demo, not a product pitch.
**Objective:** they understand the architecture well enough to critique it, and both sides know
whether there is real overlap.

---

## Adjustment from the suggested split

The proposed target was 3 / 5 / 7 / 5 / 10. Two changes, based on the repository:

**Key decisions cut from 7 to 5 minutes.** Ten decisions were identified in
[Deliverable 4](04_architectural_decisions.md), and covering them at pace produces a lecture. The
three that matter — LLM isolation, deterministic computation, provenance — are already carried by
the lifecycle walkthrough. Enumerating the rest is redundant.

**A dedicated 3-minute limitations block added.** This is not self-flagellation; it is the highest
-leverage three minutes in the meeting. Volunteering the weak points establishes that the
assessment is honest, which makes everything else more credible — and it seeds the discussion with
real problems rather than polite agreement.

Net effect: **13 minutes of presenting, 15 minutes of discussion**, weighted toward the half that
produces value.

---

## Agenda

### 0:00–0:03 · Problem and context (3 min)

*Slides 1–2*

- The failure mode, not the product: a hallucinated average looks exactly like a correct one, and
  it lands in a bid
- The four domain constraints that forced the design — existing formats, dirty data, defensible
  numbers, sensitive pricing
- One sentence for what the system is: engineers ask cost questions in plain English and get an
  answer plus the search scope that produced it

**Do not** describe features. **Do not** open the application.

---

### 0:03–0:09 · Architecture overview (6 min)

*Slides 3–5*

- The principle: the LLM translates and narrates; the application computes
- System shape: FastAPI modular monolith, PostgreSQL, two independent lifecycles meeting only at
  the database
- **One question traced end to end** — the core of this block, ~3 of the 6 minutes

Land three facts and stop:
1. The model fills a struct; it never writes SQL. Values reach the database as bound parameters
2. The number is `statistics.median()`, not a token prediction
3. Two LLM calls, two DB reads — and three of the five paths through the endpoint make zero or one
   LLM call

**Expect interruption here.** That is the good outcome. If they engage during the walkthrough,
let the block run to 7 minutes and take it from the decisions block.

---

### 0:09–0:14 · Key decisions and the trust boundary (5 min)

*Slides 6–8*

Three decisions only:

- **LLM isolation** — the outbound payload is a hand-written f-string, not a serializer. Show the
  nine lines. Whitelisting by construction; you cannot leak a field no code writes
- **Ingestion as partial success** — 497 of 500 rows land, failures persist as queryable
  data-quality rows, every record traces to its source file
- **Provenance** — scope returned on every response, captured before the query runs; provider and
  model observed rather than configured

State plainly, unprompted: **PDF ingestion is specified and not implemented.** Dependencies are
declared, requirements are written, no code path exists.

---

### 0:14–0:17 · Where this design is weak (3 min)

*Slide 9*

Five items, no hedging:

1. **Determinism starts one stage late.** The arithmetic is exact; which records get counted is an
   LLM's choice from free text. No temperature set; parameters not persisted. Mitigation: the
   parameters are returned to the user, so the variance is visible rather than hidden
2. **Retrieval is lexical.** `8" PVC WM` does not match `8-inch PVC water main`. Missed records
   lower the count silently
3. **No rate limit or spend cap** on an endpoint that spends money per call. The ledger exists;
   enforcement does not
4. **No `LIMIT`; aggregation in Python.** Fine at thousands of rows
5. **Provenance is scope-level, not record-level** — and records are withheld from the authorized
   human as an over-application of the LLM rule

**Then hand over.** Do not propose fixes; that is discussion material, and offering solutions here
converts an honest disclosure into a defensive one.

---

### 0:17–0:30 · Discussion (13 min, protected)

Four opening questions, in order:

1. **What are you building, and what does it need from cost data — to read it, or to own it?**
   Reading → CQP is a service. Owning → the conversation is schema convergence, and the risk is
   two divergent systems of record for the same data.

2. **Do you ingest the same document types?**
   If yes: the footer-placed `project_number` problem is shared, real, and unsolved on both sides.
   Offer it freely — it is the most valuable thing in the meeting that costs nothing to give away.

3. **Are you calling an LLM?**
   If yes: the provider abstraction (failover + per-call cost attribution) and the
   sanitize-by-whitelist pattern transfer immediately, independent of everything else.

4. **Where do you think this is wrong?**
   Ask it and then be quiet. An outside architect looking at the intent-parsing seam or the
   provenance gap will produce better critique in five minutes than another week of self-review.

**Close with 2 minutes for:** what each side will look at, and whether a follow-up is warranted.
Do not force an integration decision in this meeting.

---

## Timing summary

| Block | Duration | Cumulative |
| --- | --- | --- |
| Problem and context | 3 min | 0:03 |
| Architecture overview | 6 min | 0:09 |
| Key decisions and trust boundary | 5 min | 0:14 |
| Where this design is weak | 3 min | 0:17 |
| **Discussion** | **13 min** | 0:30 |

---

## Contingencies

**If they arrive with their own architecture to show** — take it first. Cut the presentation to
slides 3, 5, and 9 (principle, lifecycle, weaknesses) in 6 minutes. Understanding their system is
worth more than explaining yours, and the overlap becomes obvious faster.

**If they engage heavily during the walkthrough** — let it run. Skip the decisions block entirely;
slides 6–8 are covered implicitly by any real discussion of the lifecycle.

**If they are quiet** — go to question 4 early. "Where do you think this is wrong?" restarts a
stalled conversation better than more material does.

**If it turns into a code review** — redirect once: *"Happy to walk the repo after — for now I'm
more interested in whether the boundaries are in the right place."* If they persist, they are
telling you what they actually want; follow them.

---

## Preparation

**Have open, unshared:** `api/agent.py` (the five-step pipeline),
`services/response_generator.py:39-61` (the sanitizer), and the roadmap's footer-`project_number`
section.

**Have ready to send afterward:** [Deliverable 2](02_architecture_diagram.md) (diagrams),
[Deliverable 8](08_integration_opportunities.md) (integration options), and the footer-extraction
requirements.

**Rehearse one thing:** the sentence used when something is not built. *"That's specified and not
implemented — the dependencies are declared and the requirements are written, but there's no code
path yet."* Saying it fluently, without apology, is what keeps the rest of the meeting credible.
