# Cost Query Pro — Architecture Review

**Review date:** 2026-08-10
**Reviewed commit:** `e588792` (branch `phase_2`)
**Reviewer role:** Principal Engineer / Software Architect
**Purpose:** Prepare for a ~30-minute architecture discussion with an engineer building a
potentially complementary internal application around historical construction cost data.

---

## Scope of this review

This is a **system-architecture** review, not a code-quality audit. It evaluates boundaries,
data flow, the deterministic/generative split, provenance, security posture, extensibility,
and integration surface.

Findings are drawn from the repository as it stands at `e588792`. Where the repository does
not establish intent, this review says so rather than inferring it.

---

## Evidence legend

Every claim in these documents carries one of the following labels. This is the most important
convention in the review — the repository contains a substantial amount of well-designed
architecture that is **documented or staged but not on the live request path**, and conflating
the two would misrepresent the system in the meeting.

| Label | Meaning |
| --- | --- |
| **[IMPL]** | Implemented and reachable on a live request path |
| **[WIRED-OFF]** | Implemented and tested, but no route or caller reaches it |
| **[PARTIAL]** | Some of the described behavior exists; the rest does not |
| **[PLANNED]** | Documented in `docs/` only; no implementing code |
| **[REC]** | Reviewer recommendation; not present in the repository in any form |

---

## Deliverables

| # | Document | Contents |
| --- | --- | --- |
| 1 | [`01_architecture_summary.md`](01_architecture_summary.md) | System boundaries, responsibilities, architectural pattern |
| 2 | [`02_architecture_diagram.md`](02_architecture_diagram.md) | Mermaid diagrams, validated against the repository |
| 3 | [`03_request_lifecycle.md`](03_request_lifecycle.md) | One NL query traced end to end |
| 4 | [`04_architectural_decisions.md`](04_architectural_decisions.md) | 10 major decisions: problem, benefit, tradeoff, enterprise relevance |
| 5 | [`05_ai_architecture.md`](05_ai_architecture.md) | LLM vs. deterministic responsibility split, and where it leaks |
| 6 | [`06_security_and_trust_model.md`](06_security_and_trust_model.md) | Implemented controls vs. recommended controls |
| 7 | [`07_extensibility.md`](07_extensibility.md) | What extends cheaply, what does not, and why |
| 8 | [`08_integration_opportunities.md`](08_integration_opportunities.md) | Reusable components vs. CQP-coupled components |
| 9 | [`09_architecture_risks.md`](09_architecture_risks.md) | Critical review, classified by severity and horizon |
| 10 | [`10_presentation_outline.md`](10_presentation_outline.md) | 12-slide outline with speaker notes and timings |
| 11 | [`11_meeting_agenda.md`](11_meeting_agenda.md) | 30-minute agenda optimized for technical discussion |
| 12 | [`12_anticipated_questions.md`](12_anticipated_questions.md) | 15 questions another architect will ask (no answers, by request) |
| 13 | [`13_differentiators.md`](13_differentiators.md) | The three strongest architectural differentiators |
| 14 | [`14_what_not_to_present.md`](14_what_not_to_present.md) | What to keep out of the room, and what to hold in reserve |

---

## The five findings that most shape this review

1. **The deterministic/generative boundary is real and enforced in code**, not just documented.
   `services/analytics.py` → `services/response_generator.py` is a genuine choke point: the
   only thing crossing into the second LLM call is a five-field `CostSummary` plus the search
   scope. This is the system's strongest architectural claim and it holds up.

2. **The boundary is undermined upstream, not downstream.** The LLM chooses the search keyword
   (`services/intent_parser.py`), and that keyword is the sole determinant of which records get
   aggregated. Arithmetic is deterministic; *record selection is not*. This is the sharpest and
   most defensible criticism of the architecture, and it is worth raising before the other
   engineer does.

3. **A significant amount of built architecture is not wired in.** `services/agent_tools.py`
   (four tool definitions, 319 lines, 27 tests) and `config/prompts.py` (the entire domain
   vocabulary prompt) are imported by nothing on the request path. The roadmap marks both
   complete. Present these as *designed and staged*, never as *operating*.

4. **Provenance is scope-level, not record-level** — and the over-application of the
   raw-record rule is the cause. Raw records are correctly withheld from the LLM; they are
   *also* withheld from the authenticated human user, who is entitled to them. The original
   business goal in `docs/00_overview/00_business_scope.md` §3 explicitly asked for source
   project listings. This is a fixable architectural asymmetry, not a security requirement.

5. **The domain knowledge encoded in the roadmap is more valuable than the code.** The
   footer-placed `project_number` problem (`docs/07_checklist/00_high_level_roadmap.md`
   §"Footer-Based Project Number Extraction") is the kind of requirement only someone who has
   handled real bid tabulations would write down. It is unimplemented, and it is still the
   single most transferable asset in the repository.
