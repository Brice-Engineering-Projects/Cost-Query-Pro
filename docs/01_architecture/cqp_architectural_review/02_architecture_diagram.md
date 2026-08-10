# Deliverable 2 — Architecture Diagram

---

## Validation of the proposed diagram

The review prompt offered a candidate flow and asked that it not be assumed correct. Checked
against the repository, it is **directionally right and structurally wrong in four ways**:

| Proposed | Reality in the repository | Correction |
| --- | --- | --- |
| One linear chain from ingestion through to answer | Two **independent lifecycles** that meet only at the database. Ingestion has no LLM; querying performs no writes except the usage ledger | Split into two flows |
| "Intent Parsing" as a neutral step | Intent parsing **is an LLM call** — the first of exactly two, and the one that decides which records get counted | Mark it as an LLM boundary crossing |
| "Validation / Normalization" as a pass/fail gate | Validation is **row-isolated with partial success**; failures persist as `DataQualityIssue` rows rather than aborting the file | Show the data-quality side output |
| "Answer + Search Scope / Provenance" | Scope is real. Record-level provenance is **not returned** — the response carries `record_count` and filters only | Label scope-level, not record-level |

Additionally missing from the proposal: the authentication gate, the LLM cost ledger, and the
provider-failover path. All three are load-bearing.

---

## Diagram 1 — System context (the slide-4 diagram)

```mermaid
graph TB
    subgraph Users["Users"]
        ENG["Engineer / Estimator"]
        ADM["Administrator"]
    end

    subgraph CQP["Cost Query Pro — FastAPI modular monolith"]
        AUTH["Authentication Gate<br/>JWT HS256 · bcrypt<br/><i>core/security.py</i>"]

        subgraph WRITE["Write path — no LLM involvement"]
            ING["Ingestion Service<br/>parse · validate · dedupe<br/><i>services/ingestion.py</i>"]
        end

        subgraph READ["Read path — deterministic core"]
            SRCH["Search<br/><i>services/item_search.py</i>"]
            ANLY["Aggregation<br/><i>services/analytics.py</i>"]
            SANI["Sanitizer<br/>5 fields + scope only<br/><i>response_generator.py</i>"]
        end

        LLMB["LLM Boundary<br/>Claude primary → OpenAI fallback<br/>metered per completion<br/><i>services/llm_provider.py</i>"]
    end

    DB[("PostgreSQL<br/>cost data · lineage<br/>data quality · usage ledger")]
    EXT["External LLM providers<br/>Anthropic · OpenAI"]

    ENG -->|"NL question"| AUTH
    ENG -->|"CSV / XLSX upload"| AUTH
    ADM -->|"purge · user mgmt"| AUTH

    AUTH --> ING
    AUTH --> SRCH

    ING -->|"items · projects<br/>upload lineage<br/>quality issues"| DB
    SRCH <-->|"parameterized ORM query"| DB
    SRCH --> ANLY --> SANI
    SANI --> LLMB
    LLMB <-->|"question in · aggregates in<br/><b>no records ever</b>"| EXT
    LLMB -->|"token + cost rows"| DB

    style LLMB fill:#4a2c5e,stroke:#c77dff,stroke-width:3px,color:#fff
    style SANI fill:#1e3a5f,stroke:#4a9eff,stroke-width:3px,color:#fff
    style DB fill:#1a3a2e,stroke:#52c41a,stroke-width:2px,color:#fff
    style EXT fill:#5c2626,stroke:#ff6b6b,stroke-width:2px,color:#fff
```

**The one thing to point at:** the double-headed arrow to *External LLM providers* carries the
user's question outbound and aggregates outbound. It never carries a database row. That edge is
the whole architecture.

---

## Diagram 2 — Query lifecycle (the slide-6 diagram)

```mermaid
flowchart TD
    Q["User question<br/><i>What was the average unit cost<br/>for 8-inch PVC water main?</i>"]

    JWT{"JWT valid?"}
    Q --> JWT
    JWT -->|no| E401["401 INVALID_CREDENTIALS"]

    JWT -->|yes| RID["Assign request_id<br/><i>caller-supplied or uuid4</i>"]

    RID --> L1{{"LLM CALL 1 — intent parse<br/>sends: question only"}}
    L1 --> VAL{"Parses as<br/>SearchParameters?"}

    VAL -->|no| CLAR["200 + clarifying question<br/>usage still recorded"]

    VAL -->|yes| SCOPE["Freeze SearchScopeOut<br/><i>captured before the query runs</i>"]
    SCOPE --> DBQ["Deterministic search<br/>ILIKE + year range + optional filters<br/><i>no LIMIT</i>"]

    DBQ --> EMPTY{"Any rows?"}
    EMPTY -->|no| NORES["200 + no-records message<br/>+ full scope · usage recorded"]

    EMPTY -->|yes| AGG["Aggregate in Python<br/>count · median · mean · min · max<br/><i>statistics stdlib</i>"]

    AGG --> SAN["SANITIZE<br/>hand-built string:<br/>question + scope + 5 numbers"]

    SAN --> L2{{"LLM CALL 2 — narrate<br/>sends: aggregates only"}}
    L2 --> RESP["200 AgentQueryResponse<br/>answer · record_count · search_scope<br/>provider · model · request_id"]

    RESP --> LEDGER["Write llm_usage rows<br/>one per completion<br/>observed provider + model"]
    CLAR --> LEDGER
    NORES --> LEDGER

    style L1 fill:#4a2c5e,stroke:#c77dff,stroke-width:3px,color:#fff
    style L2 fill:#4a2c5e,stroke:#c77dff,stroke-width:3px,color:#fff
    style SAN fill:#1e3a5f,stroke:#4a9eff,stroke-width:3px,color:#fff
    style DBQ fill:#1a3a2e,stroke:#52c41a,stroke-width:2px,color:#fff
    style AGG fill:#1a3a2e,stroke:#52c41a,stroke-width:2px,color:#fff
    style SCOPE fill:#3d3416,stroke:#ffd93d,stroke-width:2px,color:#fff
```

**Three things worth pausing on:**

- **Purple stages are the only two LLM calls.** There is no loop, no tool-calling turn, no
  retry. The number of external AI calls per query is exactly two, always.
- **Scope is frozen before the query executes** (`api/agent.py:141-149`), so the returned
  provenance describes the intended search even when it returns nothing.
- **Every terminal path writes the usage ledger**, including the two that return early. This is
  a deliberate correctness property, documented at `api/agent.py:106-118`.

---

## Diagram 3 — Ingestion lifecycle

```mermaid
flowchart LR
    F["CSV / XLSX<br/>bid tabulation"]
    P["Parse<br/>csv.DictReader<br/>openpyxl read-only"]
    H["Normalize headers<br/>strip + lowercase"]
    C{"5 required<br/>columns present?"}
    R["Per-row validation<br/><i>failures isolated</i>"]
    PR["Get-or-create Project<br/><i>keyed on project_number</i>"]
    D{"Duplicate?<br/>project+desc+unit"}
    I["Insert Item<br/>+ upload_id lineage"]

    F --> P --> H --> C
    C -->|no| E422["422 INGEST_MISSING_COLUMNS<br/><i>whole file rejected</i>"]
    C -->|yes| UH["Open UploadHistory<br/>status = pending"]
    UH --> R
    R -->|invalid| DQ[("DataQualityIssue<br/>row · type · reason")]
    R -->|valid| PR
    PR -->|"no usable year"| DQ
    PR -->|ok| D
    D -->|yes| SK["skipped"]
    D -->|no| I
    I --> DB[("items")]
    SK --> RPT
    DQ --> RPT
    DB --> RPT["Close UploadHistory<br/>success | partial<br/>→ IngestReport"]

    PDF["PDF bid tab"] -.->|"PLANNED — Phase 2<br/>pdfplumber declared, unused"| P

    style PDF stroke-dasharray: 6 4,fill:#3a3a3a,stroke:#888,color:#ccc
    style DQ fill:#5c4326,stroke:#ffa940,stroke-width:2px,color:#fff
    style RPT fill:#1a3a2e,stroke:#52c41a,stroke-width:2px,color:#fff
```

**The dashed PDF node is doing real work in this diagram.** Multi-format ingestion was an
intentional design consideration from project inception — `pdfplumber` and `pdfminer-six` are
declared dependencies (`pyproject.toml:23,34`), PDF appears in the earliest scope documents,
and the extraction requirements are specified in detail. It is nonetheless **not implemented**.
Draw it dashed and say so; claiming otherwise is the fastest way to lose credibility with
another engineer who will look at the code.

---

## Diagram 4 — The trust boundary (the slide-8 diagram)

This is the one to use when the security conversation starts. It is the same system, redrawn
around *what crosses which line*.

```mermaid
graph LR
    subgraph TRUSTED["Inside the trust boundary"]
        direction TB
        RAW[("Raw cost records<br/>project names · numbers<br/>unit prices · quantities<br/>contractors · source files")]
        CALC["Deterministic computation<br/>filter · join · aggregate"]
        RAW --> CALC
    end

    subgraph GATE["Sanitizer — response_generator.py:39-61"]
        S["record_count<br/>median · average<br/>minimum · maximum<br/>+ item · state · years"]
    end

    subgraph UNTRUSTED["Outside — third-party AI"]
        LLM["Anthropic / OpenAI"]
    end

    USER["Authenticated engineer"]

    CALC --> S
    S --> LLM
    LLM -->|"prose answer"| USER
    CALC -.->|"BLOCKED TODAY<br/>records withheld from the<br/>authorized user as well"| USER

    style RAW fill:#1a3a2e,stroke:#52c41a,stroke-width:2px,color:#fff
    style S fill:#1e3a5f,stroke:#4a9eff,stroke-width:3px,color:#fff
    style LLM fill:#5c2626,stroke:#ff6b6b,stroke-width:2px,color:#fff
    style USER fill:#3d3416,stroke:#ffd93d,stroke-width:2px,color:#fff
```

**The dotted line is the most interesting thing in this review.** Withholding raw records from
the *LLM* is the correct and intended control. Withholding them from the *authenticated human
who is authorized to see them* is an over-application of that control — and it is why
provenance is currently scope-level rather than record-level, against the original business
requirement in `docs/00_overview/00_business_scope.md` §3. Discussed in
[Deliverable 9](09_architecture_risks.md), R-4.
