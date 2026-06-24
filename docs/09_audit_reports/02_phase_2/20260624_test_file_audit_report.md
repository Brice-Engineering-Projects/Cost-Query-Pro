# Test File Audit Report — Phase 2
**Date:** 2026-06-24
**Branch:** `phase_2`
**Auditor:** Claude Sonnet 4.6
**Scope:** All test files under `tests/` (smoke, unit, integration, conftest)

---

## Executive Summary

The test suite provides solid baseline coverage for the Phase 2 feature set. Core service
logic (analytics, intent parsing, response generation, LLM providers) is well-tested with
proper mocking. CRUD endpoints for projects, items, admin users, and auth are covered at the
API layer. Several **reliability issues**, **false tests**, **coverage gaps**, and
**structural problems** were identified that should be addressed before the suite can be
relied upon as a quality gate.

### Finding Severity Key
| Severity | Meaning |
|----------|---------|
| **CRITICAL** | Test gives false assurance or will likely fail in CI |
| **HIGH** | Material gap in coverage or logic defect |
| **MEDIUM** | Missing edge-case coverage that guards against real bugs |
| **LOW** | Style, fragility, or minor clarity issues |

---

## File-by-File Findings

---

### `tests/conftest.py`

#### MEDIUM — Savepoint restart condition may be unreliable
**Location:** `conftest.py:140–144`
```python
if sess.is_active and not sess.in_transaction():
    sess.begin_nested()
```
The condition `not sess.in_transaction()` may not behave identically across all SQLAlchemy
versions. If the session's `in_transaction()` returns `True` even after a nested transaction
ends, the savepoint will not be restarted and subsequent `commit()` calls inside application
code will permanently modify test data within the session. This could cause test pollution
across tests that share a fixture chain.

#### LOW — No teardown validation
The `_migrate_schema_once` fixture drops and recreates the `public` schema but provides no
assertion that the migration ran cleanly. A silently partial migration would cause
cryptic failures in every downstream test with no clear attribution.

---

### `tests/test_smoke.py`

#### LOW — No negative smoke test
The single test confirms `db_check == 1`. There is no smoke test for the unhealthy path
(e.g., a missing `db_check` key in the response), which provides no protection against
regressions in the health endpoint's response schema.

---

### `tests/unit_tests/test_auth.py`

#### MEDIUM — Fragile `token_type` assertion
**Location:** `test_login_user_form` line 31
```python
assert token_data.get("token_type", "bearer") == "bearer"
```
The `.get(..., "bearer")` default means this assertion always passes even when `token_type`
is absent from the response entirely. Replace with a direct key access:
`assert token_data["token_type"] == "bearer"`.

#### MEDIUM — Missing test for login with an unregistered username
No test exists for attempting to log in with a username that was never registered. While
this is implicitly tested by the wrong-password test, having an explicit unregistered-user
test makes the intent clearer and guards against a future code path that handles the two
cases differently.

#### MEDIUM — No assertion that password hash is not returned
`test_me_returns_current_user` confirms `username` and `is_admin` are present, but does not
assert that `password_hash` (or `password`) is absent from the response. A regression that
leaks the hash would be undetected.

#### LOW — Missing edge-case registration tests
No tests for: empty username, empty password, whitespace-only username/password, or
case-sensitivity of usernames (e.g., `TestUser` vs `testuser` treated as duplicates).

#### LOW — `test_register_short_password_rejected` assertion is implementation-coupled
**Location:** line 147
```python
assert "characters" in resp.json()["message"].lower()
```
This is valid today because `auth.py` builds the message via an f-string, but it will
silently break if the error message is refactored. The assertion should also verify the
error `code` field (`PASSWORD_TOO_SHORT`), which is more stable.

---

### `tests/unit_tests/test_auth_jwt.py`

#### CRITICAL — `test_revoked_user_rejected` is a false test
**Location:** lines 115–142

This test does not test the application's revocation logic. It:
1. Sets `user.is_admin = False`, which is **not** a disabled/revoked flag.
2. Hard-codes the check `if not user.is_admin: access_granted = False`, so `access_granted`
   will **always** be `False` regardless of application behavior.
3. Never calls any protected endpoint with the token.
4. The final `assert not access_granted` is tautologically true.

This test provides a false sense of security around token revocation. There is no actual
revocation mechanism being tested.

#### HIGH — `test_missing_sub_claim` does not test application behavior
**Location:** lines 104–112

The test decodes a token without a `sub` claim and asserts the decoded dict lacks the
key. This only tests PyJWT's behavior, not Cost Query Pro's. The comment ("In a real API,
this would trigger a 401/403") acknowledges the gap but takes no action. The test should
call a protected endpoint with the malformed token and assert a 401 response.

#### HIGH — Import inconsistency breaks test isolation guarantee
**Location:** lines 10–11
```python
from src.cost_query_pro.config.settings import settings
from src.cost_query_pro.models import User
```
All other test files import from `cost_query_pro` (without the `src.` prefix), relying on
`sys.path` manipulation in the root `conftest.py`. Using `src.cost_query_pro` creates a
second module namespace in Python, meaning `User` resolved here is a **different class
object** from the one SQLAlchemy's session uses (which was imported via `cost_query_pro`).
This can cause `isinstance()` checks and session identity tracking to fail silently,
producing incorrect ORM behavior in the `db_session` fixture.

#### MEDIUM — Token expiration and invalid signature tests are library-level, not application-level
`test_token_expiration_handling` and `test_invalid_signature_detection` test PyJWT's own
decoding logic rather than the application's route-level token validation. They have value
as documentation but should be supplemented with endpoint-level tests that send
expired/invalid tokens to a protected route and assert a 401 response.

---

### `tests/unit_tests/test_routes.py`

#### MEDIUM — Duplicate coverage with `test_auth.py`
`test_admin_purge` and `test_non_admin_forbidden` duplicate tests already present in
`test_auth.py`. The duplication adds maintenance overhead and can obscure which file is
the authoritative test for these behaviors.

#### MEDIUM — No test for items search endpoint with multiple filter combinations
The test covers a keyword search with state and year range, but there are no tests for:
- Search with only a keyword (no state/year).
- Search spanning multiple states.
- Search with pagination parameters.

#### LOW — `create_user` fixture sends form-encoded data inconsistently with other test files
**Location:** `test_routes.py:11`
```python
resp = client.post("/api/v1/auth/register", data={...})
```
The `register` endpoint accepts both JSON and form data, so this is technically valid.
However, all other test files use `json=` for registration. The inconsistency should be
documented or normalized to avoid confusion.

---

### `tests/unit_tests/test_projects.py`

#### MEDIUM — Weak pagination assertion
**Location:** `test_list_projects_pagination` line 156
```python
assert len(resp.json()) <= 2
```
With `limit=2`, 5 projects created, and a fresh DB state, the result should be **exactly**
2. Using `<=` hides a case where the endpoint returns 0 or 1 results due to a bug.
Use `assert len(resp.json()) == 2`.

#### MEDIUM — No authorization boundary tests for update/delete
There are no tests confirming that User A cannot update or delete User B's project. If the
application implements (or should implement) per-user project ownership, this security
boundary is untested.

#### LOW — No input validation tests for project fields
No tests for: invalid `state` values (more than 2 chars, lowercase, numeric),
`year` boundary values (0, negative, far future), or overly long `project_name` /
`project_number` strings.

---

### `tests/unit_tests/test_items.py`

#### MEDIUM — No input validation tests for item fields
No tests for:
- Negative `unit_price` at the CRUD endpoint level (ingest tests reject it, but the item
  creation endpoint behavior is untested for this case).
- Zero `quantity`.
- `unit_price = 0` (boundary case).
- Empty `item_description`.

#### LOW — No auth tests on utility endpoints
`GET /api/v1/items/units/distinct` and `GET /api/v1/items/stats/price-range` are tested
with valid credentials but there is no test for unauthenticated access. If they are
protected, a 401 test is missing.

---

### `tests/unit_tests/test_admin_users.py`

#### MEDIUM — `test_non_admin_cannot_delete_user` relies on implementation ordering assumption
**Location:** lines 79–86

The comment states "403 fires before the self-check." This assumes the authorization
middleware runs before the self-deletion guard. If ordering changes, targeting `users[0]`
(which could be the admin user) would trigger the wrong error code. The test should target
a known non-admin user to eliminate the ambiguity.

#### LOW — No test for demoting an admin user
No tests for removing admin status once granted (if a demotion endpoint exists).

#### LOW — No test for listing users when no users exist
The admin user is always present (created by `admin_headers`), so the empty-user-table
scenario cannot be tested without additional setup.

---

### `tests/unit_tests/test_ingest.py`

#### HIGH — No test for uploading an unsupported file type
No test for uploading a `.pdf`, `.txt`, or other non-CSV/non-XLSX file. This is a common
user error and the endpoint should return a clear error. Without this test, a regression
that accepts or crashes on bad file types would go undetected.

#### HIGH — No test for an empty file
No test for uploading a CSV or XLSX file with a header row but zero data rows, or a
completely empty file. This is a realistic edge case for the file ingestion pipeline.

#### MEDIUM — No test for `unit_price = 0` boundary
`test_upload_csv_partial_failure` confirms negative `unit_price` is rejected, but `0.00`
is not tested. Expected behavior (valid vs. rejected) is undocumented by tests.

#### MEDIUM — CSV helper does not handle values with commas
**Location:** `_csv_bytes` helper, lines 26–34

The helper builds CSV by joining values with commas but does not quote fields. If any test
value contains a comma (e.g., an item description like `"Pipe, 8 inch"`), the resulting
CSV will have incorrect column counts and produce misleading test failures.

#### LOW — No test for Excel files with multiple sheets or non-standard formatting
The XLSX helper only creates a single sheet. There is no test for workbooks with extra
sheets, blank header rows, or mixed data types in cells.

---

### `tests/unit_tests/test_analytics.py`

#### MEDIUM — No test for negative unit prices in input
The analytics layer receives items from `run_search`, which does not filter out negative
prices (those are blocked at ingest). However, if historical data or a direct DB insertion
introduces a negative price, `compute_summary` could return a negative `minimum_price`
without error. A test documenting expected behavior for negative inputs would clarify the
contract.

#### LOW — No test for very large datasets
No test verifying correctness for large item lists (e.g., 10,000+ records). The pure-Python
median/average calculation is likely correct at scale, but this is unconfirmed.

---

### `tests/unit_tests/test_intent_parser.py`

#### HIGH — No test for JSON embedded in surrounding prose
LLMs frequently return JSON wrapped in explanation text (e.g., "Here is the JSON: {...}").
The current tests only cover clean JSON and backtick-fenced JSON. A realistic failure mode
is the LLM returning `"Sure! Here are the search parameters:\n{...}"`. If `parse_intent`
does not handle this case, the query pipeline will return a parse error for a large
proportion of real inputs.

#### MEDIUM — No test for year inversion (`year_start > year_end`)
If the LLM returns `{"year_start": 2025, "year_end": 2020}`, `SearchParameters` does not
validate ordering. There is no test confirming the parser or `run_search` handles an
inverted range gracefully.

#### MEDIUM — No test for integer fields returned as strings
LLMs may return `"year_start": "2021"` (string) instead of `"year_start": 2021` (integer).
Pydantic coerces in some cases, but this behavior is version-dependent and untested.

#### MEDIUM — No test for incorrect `intent` value
If the LLM returns `"intent": "general_query"`, the `Literal["cost_search"]` field should
cause a `ValidationError` and raise `INTENT_PARSE_ERROR`. This path is not tested.

#### LOW — System prompt content assertion is implementation-coupled
**Location:** `test_parse_intent_passes_system_prompt` line 93
```python
assert "cost_search" in call_kwargs["system"]
```
A prompt refactor that preserves intent but changes wording will break this test. A simpler
check (assert the system kwarg is a non-empty string) is more robust.

---

### `tests/unit_tests/test_item_search.py`

#### MEDIUM — `test_explicit_state_adds_state_filter` comment contradicts assertion
**Location:** lines 83–88
```python
# item ilike, year_start, year_end, state
assert mock_q.filter.call_count >= 3
```
The comment lists four filters (item ilike, year_start, year_end, state), but the assertion
checks for `>= 3`. A correct assertion consistent with the comment is `>= 4`. The weaker
check `>= 3` would pass even if the state filter were removed from the implementation.

#### MEDIUM — No test for `price_min` alone or `price_max` alone
`test_price_filters_add_filters` only tests both `price_min` and `price_max` together.
Applying only one bound at a time exercises different code paths in `run_search` and is
untested.

#### LOW — No test for unit filter case-insensitivity
`run_search` applies `Item.unit.ilike(...)` for the unit filter. There is no test
confirming case-insensitive matching (e.g., `"lf"` matching records with `"LF"`).

---

### `tests/unit_tests/test_response_generator.py`

#### MEDIUM — No test for provider raising an exception
There is no test for what happens when `provider.complete()` raises inside
`generate_response`. The exception would propagate uncaught to the endpoint. A test should
confirm the exception type and message for debugging purposes.

#### MEDIUM — No test for provider returning an empty string
If `provider.complete()` returns `""`, `generate_response` returns an empty string and the
endpoint returns `answer: ""`. This is a valid degraded response but is untested.

#### LOW — `test_us_placeholder_renders_as_all_states` negative assertion is imprecise
**Location:** line 194
```python
assert "US" not in msg
```
The two-letter sequence "US" could appear in other words in the prompt template. While
unlikely to cause a false failure in practice, the assertion is not precise.

---

### `tests/unit_tests/test_llm_provider.py`

#### HIGH — No test for both providers failing in `FallbackLLMProvider`
If the primary provider fails and the fallback provider also raises an exception,
`FallbackLLMProvider.complete()` propagates the fallback's exception uncaught. There is no
test for this scenario. The endpoint would return a 500 error with no graceful handling.

#### MEDIUM — No test for fallback catching rate-limit errors
`FallbackLLMProvider` catches `anthropic.APIError` and `anthropic.APIConnectionError`.
`anthropic.RateLimitError` is a subclass of `anthropic.APIStatusError` -> `anthropic.APIError`,
so it is caught, but this is not explicitly tested or documented.

#### MEDIUM — No test for `FallbackLLMProvider.name` attribute
`FallbackLLMProvider` sets `name = "fallback"`. There is no test confirming this value,
though the agent endpoint's `provider` response field depends on it.

#### LOW — `ClaudeProvider.complete` missing test for `max_tokens` passthrough
The `complete` method accepts `max_tokens`. There is no test confirming the value is
forwarded to the Anthropic client.

---

### `tests/unit_tests/test_agent_tools.py`

#### HIGH — `execute_tool` only tested with `keyword_search`
**Location:** `TestExecuteTool` class

`execute_tool` is a dispatcher for four tools. Only the `keyword_search` dispatch path
is tested via `execute_tool`. The dispatcher's routing logic for `filter_search`,
`price_stats`, and `project_lookup` is untested.

#### MEDIUM — No test for `execute_tool` propagating `AppError("NO_RESULTS")`
If any handler raises `AppError("NO_RESULTS", ...)`, `execute_tool` should propagate it.
This behavior is not tested and could be silently broken by a future modification.

#### MEDIUM — No test for `handle_keyword_search` when `compute_summary` raises
When `run_search` returns `[]`, `compute_summary([])` raises `AppError("NO_RESULTS")`. There
is no test confirming this exception propagates correctly through `handle_keyword_search`.

#### LOW — `test_all_tools_list_is_complete` hardcodes the count `4`
If a fifth tool is added, a developer must remember to update this assertion. A structural
check (e.g., verify `ALL_TOOLS` equals all module-level `*_TOOL` constants) would be more
robust.

---

### `tests/unit_tests/test_agent_endpoint.py`

#### HIGH — No test for empty or whitespace-only question
The `AgentQueryRequest` schema requires `question` with `min_length=1`. No test confirms
that `{"question": ""}` is rejected with 422 (Pydantic validation).

#### HIGH — No test for non-`INTENT_PARSE_ERROR` `AppError` being re-raised
The `agent_query` handler re-raises any `AppError` from `parse_intent` that is not
`INTENT_PARSE_ERROR`. This path is untested and any regression here would go undetected.

#### HIGH — No test for non-`NO_RESULTS` `AppError` from the search/analytics step
Similarly, any `AppError` other than `NO_RESULTS` raised by `run_search` or
`compute_summary` should propagate and produce a 5xx response. This is currently untested.

#### MEDIUM — `test_no_results_returns_friendly_message` relies on fragile string matching
**Location:** line 204
```python
assert "No records" in body["answer"]
```
This hard-codes expected wording from the implementation. If the message changes, the test
fails. An assertion on `record_count == 0` combined with a non-empty `answer` string is
more stable.

#### MEDIUM — `TestAgentQueryAuth` modifies global `app.dependency_overrides` without concurrency safety
**Location:** lines 161–170

The class-based test modifies the global `app.dependency_overrides` dict. If parallel test
execution is added (e.g., via `pytest-xdist`), global mutation could cause interference
between test workers.

#### LOW — No test confirming the `model` field contains a non-empty string
The `model` field is included in every response but is never asserted.

---

## Structural Issues

### CRITICAL — Integration tests live in `unit_tests/`; `integration_tests/` directory is empty

The following test files are **integration tests** (require a live database, run full HTTP
request cycles through FastAPI/SQLAlchemy) but reside in `tests/unit_tests/`:

- `test_auth.py`
- `test_auth_jwt.py`
- `test_admin_users.py`
- `test_ingest.py`
- `test_items.py`
- `test_projects.py`
- `test_routes.py`

The `tests/integration_tests/` directory exists but contains only `__init__.py`. This
mislabeling prevents CI from running integration vs. unit tests separately (e.g., fast unit
tests on every commit, integration tests only on PR builds).

True unit tests (no DB, all I/O mocked):
- `test_analytics.py`
- `test_intent_parser.py`
- `test_response_generator.py`
- `test_item_search.py`
- `test_agent_tools.py`
- `test_llm_provider.py`

`test_agent_endpoint.py` is a hybrid: uses `TestClient` but mocks all I/O dependencies.

---

## Summary Table

| File | CRITICAL | HIGH | MEDIUM | LOW | Total |
|------|----------|------|--------|-----|-------|
| `conftest.py` | 0 | 0 | 1 | 1 | 2 |
| `test_smoke.py` | 0 | 0 | 0 | 1 | 1 |
| `test_auth.py` | 0 | 0 | 3 | 2 | 5 |
| `test_auth_jwt.py` | 1 | 2 | 1 | 0 | 4 |
| `test_routes.py` | 0 | 0 | 2 | 1 | 3 |
| `test_projects.py` | 0 | 0 | 2 | 1 | 3 |
| `test_items.py` | 0 | 0 | 1 | 1 | 2 |
| `test_admin_users.py` | 0 | 0 | 1 | 2 | 3 |
| `test_ingest.py` | 0 | 2 | 2 | 1 | 5 |
| `test_analytics.py` | 0 | 0 | 1 | 1 | 2 |
| `test_intent_parser.py` | 0 | 1 | 3 | 1 | 5 |
| `test_item_search.py` | 0 | 0 | 2 | 1 | 3 |
| `test_response_generator.py` | 0 | 0 | 2 | 1 | 3 |
| `test_llm_provider.py` | 0 | 1 | 2 | 1 | 4 |
| `test_agent_tools.py` | 0 | 1 | 2 | 1 | 4 |
| `test_agent_endpoint.py` | 0 | 3 | 2 | 1 | 6 |
| **Structural** | 1 | 0 | 0 | 0 | 1 |
| **TOTALS** | **2** | **10** | **27** | **17** | **56** |

---

## Priority Remediation Recommendations

### P0 — Address before merging to `main`

1. **Fix `test_auth_jwt.py` imports** — change `from src.cost_query_pro...` to
   `from cost_query_pro...` to prevent a dual-module namespace that corrupts ORM identity.
2. **Rewrite `test_revoked_user_rejected`** — replace with an actual endpoint call using a
   token for a known-inactive user, or remove entirely until a revocation mechanism is
   implemented.
3. **Rewrite `test_missing_sub_claim`** — call a protected endpoint with the malformed token
   and assert a 401 response.

### P1 — Address in a follow-up PR (before enabling CI quality gates)

4. Add test for unsupported file type upload in `test_ingest.py`.
5. Add test for empty file upload in `test_ingest.py`.
6. Add tests for empty/whitespace question in `test_agent_endpoint.py`.
7. Add tests for non-`INTENT_PARSE_ERROR` and non-`NO_RESULTS` `AppError` propagation paths
   in `test_agent_endpoint.py`.
8. Add `execute_tool` dispatch tests for `filter_search`, `price_stats`, and `project_lookup`
   in `test_agent_tools.py`.
9. Add test for `FallbackLLMProvider` when both providers fail in `test_llm_provider.py`.
10. Fix the state filter assertion count from `>= 3` to `>= 4` in `test_item_search.py`.

### P2 — Address as part of ongoing quality improvement

11. Move integration tests to `tests/integration_tests/` and configure CI to run them
    independently from pure unit tests.
12. Add embedded-prose JSON test to `test_intent_parser.py`.
13. Add year inversion test (`year_start > year_end`) to `test_intent_parser.py`.
14. Fix the `token_type` default-value assertion in `test_auth.py`.
15. Add `password_hash` not-present assertion to the `/me` test in `test_auth.py`.
16. Fix pagination assertion to use `== 2` instead of `<= 2` in `test_projects.py`.
17. Add test for JSON with intent embedded in prose to `test_intent_parser.py`.

---

*End of audit report.*
