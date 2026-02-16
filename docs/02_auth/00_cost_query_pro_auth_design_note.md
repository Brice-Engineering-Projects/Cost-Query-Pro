
# Cost Query Pro — Authentication Contract & Auth Flow Hardening (Internal Engineering Design Note)

**Status:** Draft for Engineering Review
**Scope:** Backend Auth Contract, Routing, Error Taxonomy, Observability, Tests
**Owners:** Backend Platform (FastAPI)
**Last Updated:** 2025-09-01

---

## 1) Purpose & Outcome

This document specifies the change from a form-encoded login contract to a JSON login contract for `POST /api/v1/auth/login`, and consolidates related hardening items discovered during recent auth testing. JSON Web Token (JWT) usage remains unchanged (HS256 with `SECRET_KEY` and configurable expiry). The outcome is a consistent, documented, and testable authentication surface aligned with the API reference and Pydantic v2.

---

## 2) Background & Current State

### 2.1 Architecture Context

- Framework: FastAPI (Python)
- ORM: SQLAlchemy
- Validation: Pydantic v2
- Auth: JWT (HS256), bearer tokens on protected routes
- Runtime & tooling: `uv`, `uvicorn`, pytest
- Relevant modules: `app/api/auth.py`, `app/core/security.py`, `app/config/settings.py`, `app/schemas/*`

### 2.2 Current Login Contract (Form-Encoded)

- Endpoint: `POST /api/v1/auth/login`
- Content-Type: `application/x-www-form-urlencoded`
- Request body (key/value): `username=<str>&password=<str>`
- FastAPI dependency: `OAuth2PasswordRequestForm`
- Response (success): `{ "access_token": "<jwt>", "token_type": "bearer" }`
- JWT configuration: algorithm **HS256**, secret **SECRET_KEY**, expiry via **ACCESS_TOKEN_EXPIRE_MINUTES** (see `settings.py`)

### 2.3 Observed Issues (Recent Testing)

- 404 on `/login` and `/api/v1/auth/login` due to inconsistent router prefixes.
- 422 on `POST /api/v1/auth/login` when clients sent JSON to a form-encoded route.
- 500 on `/auth/me` due to missing import for `status` in security utilities.
- Pydantic v2 incompatibility: `orm_mode` deprecated; requires `ConfigDict(from_attributes=True)` or `model_validate(..., from_attributes=True)`.
- Noisy bcrypt warnings and out-of-date dependencies.
- Lack of explicit error taxonomy and route-map observability.

---

## 3) Goals, Non‑Goals, and Constraints

### 3.1 Goals

- Standardize `/auth/login` to a **JSON** contract.
- Normalize routing to **`/api/v1/auth/*`** without double prefixes.
- Fully align response models with **Pydantic v2** behavior.
- Establish a clear **error taxonomy** for auth paths (401/403).
- Provide minimal yet effective **tests** for token issuance and protected access.
- Improve **observability** (route map on startup, structured 401/403 logs).
- Document the contract in the API reference and publish example requests.

### 3.2 Non‑Goals (for this change set)

- Implementing refresh tokens and rotation (planned later).
- Migrating to RS256 or key rotation (tracked for a subsequent phase).
- Introducing centralized revocation/denylist with Redis (tracked later).
- SSO or external IdP integration (Auth0 etc.).

### 3.3 Constraints

- Backwards compatibility may be required for existing form clients (optional grace period).
- Pydantic v2 must be used consistently across read models and conversions.

---

## 4) Design Decisions

### 4.1 Contract: JSON Login (Decision: **Adopt**)

- **Request**: `POST /api/v1/auth/login` with JSON body `{ "username": "<str>", "password": "<str>" }`.
- **Response**: `{ "access_token": "<jwt>", "token_type": "bearer" }` (unchanged).
- **Rationale**: Aligns with API documentation, simplifies client integration, avoids mixed encodings.

### 4.2 Routing Normalization (Decision: **Enforce**)

- Router prefix: `router = APIRouter(prefix="/auth", tags=["auth"])`
- Inclusion: `app.include_router(auth.router, prefix="/api/v1")`
- Resulting paths: `/api/v1/auth/login`, `/api/v1/auth/me`, etc.
- Startup hook prints a route map to detect misconﬁguration early.

### 4.3 Pydantic v2 Compliance (Decision: **Enforce**)

- Response models must declare `model_config = ConfigDict(from_attributes=True)`.
- Where appropriate, use `Model.model_validate(obj, from_attributes=True)` to validate from ORM instances.
- Removes `orm_mode` and eliminates v2 warnings.

### 4.4 Token Strategy (Decision: **Access Token Only**, 60 minutes)

- Single access JWT with 60‑minute expiry (configurable).
- Token location: `Authorization: Bearer <token>` header.
- Refresh tokens and rotation to be introduced in a later milestone.

### 4.5 Error Taxonomy (Decision: **Standardize**)

- **401 Unauthorized**: invalid credentials, missing/invalid/expired token, disabled user.
- **403 Forbidden**: authenticated principal lacks required role (RBAC to be added later).
- Responses must avoid leaking credential details or user existence.

### 4.6 Observability & DevEx (Decision: **Add**)

- Route map logging at startup.
- Structured logs for 401/403 with reason codes (no sensitive data).
- Optional `X-Request-ID` middleware for correlation across logs.
- `uv` tasks / Make targets to smoke test login and `/me` locally.

### 4.7 Dependency Hygiene (Decision: **Pin & Audit**)

- Quiet bcrypt warnings with compatible pins (e.g., `passlib[bcrypt]==1.7.4`, `bcrypt>=4.1.2`).
- Keep `fastapi/starlette/pydantic` at patched versions.
- Add `pip-audit` (or `safety`) to CI; fail builds on critical vulnerabilities.

---

## 5) Detailed Specification

### 5.1 API Contracts

#### 5.1.1 `POST /api/v1/auth/login`

- **Purpose**: Authenticate credentials and issue a bearer token.
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:

  ```json
  { "username": "example_user", "password": "example_password" }
  ```

- **Success (200)**:

  ```json
  { "access_token": "<jwt>", "token_type": "bearer" }
  ```

- **Failure (401)**:

  ```json
  { "detail": "Invalid credentials" }
  ```

- **Validation Errors (422)**: Standard Pydantic error structure.
- **Notes**: During a grace period, the route may accept `application/x-www-form-urlencoded` with the same semantics for backward compatibility.

#### 5.1.2 `GET /api/v1/auth/me`

- **Purpose**: Return the authenticated principal.
- **Request Headers**: `Authorization: Bearer <token>`
- **Success (200)**:

  ```json
  { "id": 1, "username": "example_user", "is_admin": false }
  ```

- **Failure (401)**:

  ```json
  { "detail": "Invalid or expired token" }
  ```

### 5.2 Security Considerations

- **Token Creation**: HS256 signed JWT containing `sub`, `iat`, `exp`.
- **Secret Management**: `SECRET_KEY` via environment variable; never logged.
- **Transport**: HTTPS required in deployment environments.
- **Data Minimization**: Tokens must avoid embedding sensitive fields.
- **Abuse Prevention**: Login endpoint is a DoS/misuse target; basic rate‑limit strategy to be added with Redis counters in a follow‑up.

### 5.3 Error Handling

- Standardize `HTTPException` messages.
- Avoid user‑enumeration vectors (never distinguish “unknown user” vs “bad password”).
- Log reason codes internally (e.g., `auth_err=expired`, `auth_err=invalid_signature`).

### 5.4 Observability

- **Route Map**: print method and path on startup for all routes.
- **Security Logs**: record 401/403 with reason codes and request IDs.
- **Metrics** (future): counters for login attempts, 401/403 occurrences, and token validations.

---

## 6) Migration & Rollout

### 6.1 Options

- **Immediate Cutover**: JSON‑only now; update clients and documentation simultaneously.
- **Grace Period (Recommended)**:
  - Phase 1: Accept both JSON and form; prefer JSON in documentation and examples; emit warning logs for form usage.
  - Phase 2: Remove form acceptance; treat JSON as the single contract.

### 6.2 Backward Compatibility

- Clients posting `application/x-www-form-urlencoded` continue to function during the grace period.
- Swagger UI “Authorize” flow may still rely on `tokenUrl`; this remains for compatibility, even as the handler accepts JSON.

### 6.3 Communication

- Update API reference examples to JSON.
- Publish Insomnia/Postman environment snippets showing JSON contract.
- Note deprecation timeline if a grace period is selected.

---

## 7) Testing Strategy

### 7.1 Unit & Integration Coverage

- Login success (JSON) → 200 + token.
- Login failure (bad credentials) → 401.
- `/auth/me` without token → 401.
- `/auth/me` with valid token → 200 + principal.
- Expired token → 401.
- (If grace period) login success (form) → 200 + token.

### 7.2 Fixtures

- Dedicated test database or transactional SQLite with SQLAlchemy.
- Seeded test user with known password hash.
- Clock control for token expiry tests where practical.

### 7.3 CI

- `pytest -q` as part of PR checks.
- `pip-audit` (or `safety`) against `pyproject.toml` / lockfiles; block merges on critical issues.

---

## 8) Dependency & Version Policy

- Authentication stack: `PyJWT>=2.9.0`, `passlib[bcrypt]==1.7.4`, `bcrypt>=4.1.2`.
- FastAPI/Starlette/Pydantic pinned to recent patched versions.
- Regular dependency audits; renovate/dependabot recommended.

---

## 9) Operational Tasks & DevEx

### 9.1 Local Development

- Start server: `uv run uvicorn app.main:app --reload`
- Smoke test (curl):

  ```bash
  TOKEN=$(curl -sS -X POST http://localhost:8000/api/v1/auth/login         -H "Content-Type: application/json"         -d '{"username":"brice","password":"secret123"}' | jq -r .access_token)
  curl -sS http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
  ```

### 9.2 Logging

- Ensure logs exclude secrets and token contents.
- Record correlation/request IDs when available.

### 9.3 Documentation

- API reference to show JSON request bodies for `/auth/login` and the bearer header convention for protected routes.
- Internal docs to include error taxonomy and examples of 401/403 payloads.

---

## 10) Risks & Mitigations

- **Client Breakage**: Clients sending form-encoded bodies may fail after removal → Mitigate with a defined grace period and deprecation notice.
- **Misconfigured Routes**: Prefix drift can reintroduce 404s → Mitigate by logging route map at startup and covering with endpoint tests.
- **Pydantic v2 Mismatch**: Missing `from_attributes` may cause serialization errors → Mitigate by enforcing configuration in read models and validating in tests.
- **Security Regression**: Looser error messages can leak signals → Mitigate with standardized messages and internal reason codes only.

---

## 11) Acceptance Criteria (Definition of Done)

- `/api/v1/auth/login` accepts JSON and returns a bearer token on successful authentication.
- `/api/v1/auth/me` returns the authenticated principal with a valid token and rejects invalid/expired tokens with 401.
- Route map prints on startup and shows `/api/v1/auth/*` paths only once (no duplicate prefixes).
- No Pydantic v2 warnings during normal operation.
- Minimal test suite passes locally and in CI.
- Dependency audit shows no critical issues.
- API reference updated; Insomnia/Postman samples provided.
- Decision on grace period vs immediate cutover documented and communicated.

---

## 12) Appendices

### A) Example Pydantic v2 Read Model (from_attributes)

```python
from pydantic import BaseModel, ConfigDict

class UserRead(BaseModel):
    id: int
    username: str
    is_admin: bool
    model_config = ConfigDict(from_attributes=True)
```

### B) Example Token Payload (minimal)

```json
{ "sub": "example_user", "iat": 1725148800, "exp": 1725152400 }
```

### C) Route Map Logging (conceptual)

```python
@app.on_event("startup")
async def print_routes():
    for r in app.routes:
        methods = getattr(r, "methods", None) or []
        print(f"[route] {methods} {getattr(r, 'path', '')}")
```

### D) Insomnia Profile Snippet (JSON Login)

- Method: `POST`
- URL: `http://localhost:8000/api/v1/auth/login`
- Headers: `Content-Type: application/json`
- Body:

  ```json
  { "username": "brice", "password": "secret123" }
  ```

- Test: extract `access_token` and set environment variable for Bearer auth.
- Protected calls include header: `Authorization: Bearer {{ access_token }}`

### E) Make/Just Tasks (example)

```makefile
auth-dev:
    uv run uvicorn app.main:app --reload

auth-smoke:
    @curl -sS -X POST http://localhost:8000/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username":"brice","password":"secret123"}' | jq .
```

---

## 13) Open Questions

- Refresh token model: cookie vs header, rotation strategy, and replay protection.
- HS256 → RS256 migration plan and key rotation cadence.
- Centralized revocation semantics and operational SLOs for token invalidation.
- Rate limiting thresholds for `/auth/login` and observability metrics to watch.

---

_**End of Document**_
