# Cost Query Pro - Secure AI Query Architecture

## Overview

Cost Query Pro uses a hybrid AI architecture designed to provide a natural language search experience while minimizing exposure of proprietary project data to third-party AI providers.

The guiding principle is:

> The AI interprets user intent and explains results. The application performs all database access and analytics.

This approach allows Cost Query Pro to leverage Claude and GPT for conversational interactions without granting direct access to the database.

---

# High-Level Workflow

```text
User
  ↓
Claude (Intent Parsing)
  ↓
Structured Search Request
  ↓
FastAPI Backend
  ↓
PostgreSQL Database
  ↓
Analytics Layer
  ↓
Claude (Response Generation)
  ↓
User
```

---

# Detailed Request Flow

## Step 1 - User Submits Question

Example:

```text
What have Florida utilities been paying for 24-inch ductile iron pipe over the last five years?
```

The user's question is sent to the LLM.

At this stage:

* No database access occurs.
* No project data is exposed.
* The model is only asked to interpret intent.

---

## Step 2 - LLM Converts Question into Structured Search Parameters

The LLM returns a structured payload.

Example:

```json
{
    "intent": "cost_search",
    "item": "24-inch ductile iron pipe",
    "state": "FL",
    "year_start": 2021,
    "year_end": 2026
}
```

Important:

The LLM does NOT generate SQL.

The LLM only extracts search criteria from the user's question.

---

## Step 3 - FastAPI Performs Database Search

The backend validates the search request and constructs database queries internally.

Example:

```python
search_request = SearchRequest(
    item="24-inch ductile iron pipe",
    state="FL",
    year_start=2021,
    year_end=2026,
)

results = item_service.search(search_request)
```

The backend is solely responsible for:

* Query generation
* Authorization
* Validation
* Database access

The LLM never communicates directly with PostgreSQL.

---

## Step 4 - PostgreSQL Returns Records

The database returns matching records.

Example:

```json
[
    {
        "unit_price": 212.00,
        "state": "FL",
        "year": 2023
    },
    {
        "unit_price": 225.00,
        "state": "FL",
        "year": 2024
    }
]
```

At this stage, all raw data remains inside Cost Query Pro infrastructure.

---

## Step 5 - Analytics Layer Generates Summary Statistics

The backend computes analytical results.

Example:

```python
summary = {
    "record_count": 147,
    "median_price": 212,
    "average_price": 219,
    "minimum_price": 180,
    "maximum_price": 287
}
```

Additional calculations may include:

* Median
* Mean
* Percentiles
* Trend analysis
* Inflation adjustments
* Regional comparisons
* Outlier detection

---

## Step 6 - Sanitized Summary Sent to LLM

Only aggregated results are provided to the LLM.

Example:

```json
{
    "record_count": 147,
    "median_price": 212,
    "average_price": 219,
    "minimum_price": 180,
    "maximum_price": 287
}
```

The following information is NOT transmitted:

* Project names
* Project numbers
* Contractor names
* Bid tabulations
* Uploaded source files
* Internal notes
* Raw database tables

---

## Step 7 - LLM Generates User-Friendly Response

The LLM transforms the summary into natural language.

Example:

```text
Based on 147 Florida projects between 2021 and 2026, the median unit cost for 24-inch ductile iron pipe was approximately $212 per LF. Costs ranged from $180 to $287 per LF, with an average cost of $219 per LF.
```

---

# Security Model

## AI Responsibilities

The LLM is responsible for:

* Intent recognition
* Search parameter extraction
* Natural language generation
* User interaction

The LLM is NOT responsible for:

* Database access
* Query execution
* Business rules
* Cost calculations
* Authorization decisions

---

## Backend Responsibilities

The FastAPI backend is responsible for:

* Authentication
* Authorization
* SQL generation
* Database access
* Data validation
* Statistical analysis
* Audit logging

---

# Future Enterprise Deployment

For enterprise customers with stricter security requirements, the architecture can be modified to eliminate the second LLM call.

```text
User
  ↓
Claude
  ↓
Structured Search Request
  ↓
FastAPI
  ↓
PostgreSQL
  ↓
Analytics Layer
  ↓
Template-Based Response
  ↓
User
```

In this model:

* Only the user's question leaves the environment.[01_secure_ai_query_architecture.md](01_secure_ai_query_architecture.md)
* Project data never leaves the infrastructure.
* No database-derived information is transmitted to external AI providers.

---

# Key Design Principle

The AI should function as a translator and narrator, not as a database operator.

Database access remains deterministic, auditable, and fully controlled by the application backend while the AI provides the conversational experience expected by modern users.
