# Deliverable 13 — Three Strongest Architectural Differentiators

**Standard applied.** A differentiator must be (a) present in the repository or in written
requirements, (b) not what a competent engineer would produce by default, and (c) consequential —
something breaks or degrades without it.

Several plausible candidates were **rejected** under this standard, listed at the end. Being
explicit about what did not qualify is part of not manufacturing differentiators.

---

## Differentiator 1 — The LLM data boundary is enforced by construction, not by policy

### What it is

The outbound payload to the narration LLM call is a **hand-written f-string** containing the
user's question, three scope fields, and five numbers — assembled by
`services/response_generator.py:39-61`. There is no serializer, no `model_dump()`, no iteration
over an ORM object anywhere in the LLM path.

The complete list of what leaves the environment:

| Call | Payload |
| --- | --- |
| 1 — intent parse | Static system prompt + the user's question |
| 2 — narrate | Static system prompt + question + `item`, `state`, year range + five numbers |

Never: project names, project numbers, contractor names, individual unit prices, quantities,
uploaded file contents, filenames, usernames, user IDs.

### Why it matters

The industry default is *filter before serializing* — build a dict, drop the sensitive keys, send
the rest. That approach **fails open**: add a column to `Item`, and it appears in the next
`model_dump()` with nobody noticing. The failure is silent, and it surfaces as a data-exposure
incident rather than a test failure.

Whitelist-by-construction inverts the failure mode. You cannot leak a field that no line of code
writes. Adding a column to `Item` cannot change this payload, because nothing here reads `Item`.
The guarantee is structural rather than procedural — a property of the code's shape, not of anyone
remembering a rule.

The secondary benefit is that **the control is auditable in thirty seconds**. Nine lines fit on a
slide. "We sanitize before sending to the LLM" is an unfalsifiable claim in most systems; here it
is a function you can read in full.

### Evidence

- `services/response_generator.py:39-61` — the sanitizer, f-string construction
- `services/intent_parser.py:55` — signature takes no `Session`; structurally cannot reach the DB
- `services/analytics.py`, `services/item_search.py` — import no LLM SDK
- `services/llm_provider.py` — the only module in `src/` importing `anthropic` or `openai`
- `tests/unit_tests/test_response_generator.py:150` — asserts eight forbidden field names absent
- `api/agent.py:155-172` — empty result sets never reach a second LLM call
- `docs/03_api/01_secure_ai_query_architecture.md` — the boundary specified before it was built

### Classification

**Technical implementation advantage.** The domain motivated it — bid pricing is competitively
sensitive — but the differentiator is the implementation *technique*, which transfers to any
application sending data to a third-party model.

### Honest qualification

This protects the **outbound** path completely. It says nothing about which records were selected
in the first place, and it is *over*-applied on one axis: records are also withheld from the
authenticated human user, who is authorized to see them (see
[Deliverable 9](09_architecture_risks.md) R-4).

---

## Differentiator 2 — Ingestion treats dirty engineering data as the normal case

### What it is

A file is neither accepted nor rejected. Each row is validated independently; failures are
isolated, counted, and **persisted as `DataQualityIssue` rows keyed to the upload**; the response
is a structured `IngestReport` with inserted / skipped / failed counts and a per-row issue list.
Around it, a lineage ring: `UploadHistory` records who uploaded which file when with what outcome,
and `items.upload_id` is a real FK from every cost record back to its source.

### Why it matters

Bid tabulation data is genuinely dirty — merged cells, subtotal rows, notes in numeric columns,
inconsistent units, agency-specific conventions. The default engineering instinct is
transactional all-or-nothing, and it is the wrong instinct here: a 500-row file with 3 bad rows
produces zero rows and an unactionable error, and every upload becomes a support ticket.

Three consequences follow from getting this right:

1. **Ingestion is self-service.** 497 rows land; the operator learns exactly which 3 failed and
   why, fixes them, and re-uploads safely because the composite dedupe key
   `(project_number, item_description, unit)` skips what is already present. No developer involved.
2. **Data quality becomes queryable.** Because issues *persist* rather than only appearing in an
   HTTP response, recurring problems become analyzable over time — the model's own docstring names
   the intent: detecting patterns of format problems from particular agencies
   (`models/data_quality_issue.py:5-8`). That is a governance capability, not error handling.
3. **Every price is traceable.** `items.upload_id` with `ON DELETE SET NULL` means deleting an
   upload record degrades lineage rather than destroying cost data — the right asymmetry for this
   domain.

This is the most complete subsystem in the repository and it is the one most likely to be
genuinely reusable.

### Evidence

- `services/ingestion.py:176-258` — per-row validation with isolated failures
- `services/ingestion.py:196-203, 214-221` — `DataQualityIssue` written on both failure classes
- `services/ingestion.py:226-229` — idempotency check
- `services/ingestion.py:244-248` — `partial` as a terminal status distinct from `success`
- `models/upload_history.py`, `models/data_quality_issue.py`, `models/item.py:38-42`
- `schemas/ingest.py` — `IngestReport` as the structured contract

### Classification

**Both.** The design pattern is technical; knowing that engineering source data *requires* it is
domain knowledge. An engineer without bid-tab exposure builds the transactional version first.

### Honest qualification

One inconsistency undercuts it: a malformed state code is silently replaced with `"XX"`
(`services/ingestion.py:72-73`) with **no** `DataQualityIssue` record — the single place this
pipeline degrades data without saying so. It is an open roadmap item (Q-8). `UploadHistory.status`
is also free text rather than a constrained enum.

---

## Differentiator 3 — Domain requirements that only come from having done the work

### What it is

The roadmap contains a class of requirement that cannot be derived from a data model, a framework,
or a competitor. The clearest example:

> Bid tabulations routinely place `project_number` in a **page footer or trailing row**, not in a
> data column. Ingestion must scan trailing rows, validate candidates against the same rules as
> header-sourced values, and reject files with **multiple conflicting candidates** via a distinct
> `INGEST_AMBIGUOUS_PROJECT_NUMBER` error rather than guessing.

Around it: pipe-type taxonomy with practical distinctions (DIP, PVC, HDPE, RCP, CIPP and where each
is actually used), diameter conventions mapped to the words engineers use ("large" = 18–36",
"transmission" = 24"+), unit abbreviations tied to what they measure, installation methods
(open cut, HDD, auger bore, pipe bursting, microtunnel), and cost drivers ranked by influence.

### Why it matters

The footer requirement is architecturally consequential, not cosmetic. The current pipeline is
strictly row-oriented — `_get_or_create_project()` reads `row["project_number"]` and nothing
carries document-level context. Supporting footers requires a **document-context object** merged
into each row before validation. That is a structural change, and it was identified *before* the
implementation, which is why the change is tractable rather than a rewrite.

The ambiguity guard is the detail that signals real experience. The naive implementation scans for
a project-number-shaped string and takes the first match. Someone who has processed real bid tabs
knows that trailing rows contain several plausible candidates — a solicitation number, an addendum
reference, a sheet code — and that guessing wrong misattributes an entire file's cost records to
the wrong project. Silently. Failing loudly on ambiguity is the correct and non-obvious choice.

The same applies to the vocabulary: "large diameter Jack and Bore" is a question an estimator asks
and a dropdown cannot express. Encoding that "large" means 18–36 inches is the difference between
a system engineers use and one they work around.

### Evidence

- `docs/07_checklist/00_high_level_roadmap.md` §"Footer-Based Project Number Extraction" — scan
  depth, pattern, validation parity, ambiguity guard, test matrix
- Same file, §Ingestion Pipeline, marked `[!]` as a **known gap** with the exact failure named:
  affected files fail with `INGEST_MISSING_COLUMNS`
- `config/prompts.py:20-56` — the domain vocabulary, in detail
- `docs/00_overview/00_business_scope.md` §3 — the original goal phrased in domain terms
- `pyproject.toml:23,34` — `pdfplumber`, `pdfminer-six` declared from early on

### Classification

**Domain-knowledge advantage, unambiguously.** No amount of software skill produces the footer
requirement. It comes from having opened bid tabs.

### Honest qualification — and why it still qualifies

**None of this is implemented.** Footer extraction is unbuilt. `config/prompts.py` is **imported by
nothing**, so the vocabulary is not in the live prompts. PDF ingestion does not exist.

It qualifies anyway, for two reasons. First, the requirements are *written down with enough
precision to implement* — including the failure mode, the error code, and the test cases — which
is the hard part and the part that does not come from the codebase. Second, it is the most
*transferable* asset here: if the other engineer ingests bid tabs, this problem is real for them
too, and handing it over costs nothing.

**Present it as domain insight ahead of implementation, never as a capability.** That framing is
accurate and is actually more impressive — being ahead of a problem is a better position than
having quietly shipped around it.

---

## Candidates considered and rejected

Recorded so the three above are credible by contrast.

| Candidate | Why rejected |
| --- | --- |
| **LLM provider abstraction with failover** | Genuinely well built, and the observed-model cost attribution is a nice catch. But a Protocol with two implementations and a try/except is standard practice. **Strongest reuse candidate** ([D8](08_integration_opportunities.md) §1.1); not a differentiator |
| **Per-completion cost ledger** | Correct NULL semantics for unpriced models and the right build order. Increasingly common in production LLM systems, and **enforcement is unbuilt** — it observes cost without constraining it |
| **Search scope in the response** | Real and valuable, and it makes the parse non-determinism visible. But it is one struct copied into the response, and the more distinctive version — record-level provenance — is precisely what is missing |
| **Two-call pipeline rather than an agentic loop** | Defensible and correct for the use case. It is also the *simpler* choice, and the tool-calling alternative is written and unwired — hard to claim as a considered architectural position |
| **Deterministic computation over LLM computation** | The core principle, and it is real. But it is *the premise of the review*, not something discovered in the repository — and [D5](05_ai_architecture.md) §3.1 establishes it holds for arithmetic, not for record selection. Overclaiming here would undercut the review |
| **JWT auth, `AppError` taxonomy, Alembic, `mypy --strict` CI** | Competent baseline engineering. Table stakes |

---

## How to use these in the meeting

**Differentiator 1** is the credibility opener — it is concrete, verifiable in thirty seconds, and
better than the industry default. Show the nine lines.

**Differentiator 2** is the one most likely to produce a real integration conversation, because it
solves a problem the other engineer probably has and probably underestimated.

**Differentiator 3** is the one to give away. It costs nothing, it is the most transferable thing
in the repository, and offering an unsolved problem you understand deeply is a stronger signal
than presenting a solved one.

**All three share a property worth naming explicitly:** each came from taking a domain constraint
seriously rather than from choosing a technology. That is the through-line of this architecture,
and it is the most useful thing another engineer can take away from the meeting.
