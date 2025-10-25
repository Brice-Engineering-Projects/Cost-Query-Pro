---
title: Tasks Checklist
date: 2025-08-02
module: Tasks Checklist
type: project
tags:
author: Brice Nelson
author_link: https://github.com/Brice-Engineering-Projects/Cost-Query-Pro
status: On-going
---

# Cost Query Pro

## Tasks Checklist

## Summary Table

### 📋 Task Summary Overview

| Category | Description | Progress | Priority |
|-----------|--------------|-----------|-----------|
| **Documentation** | API reference, OpenAPI schema, deployment, and developer documentation. | ☐ 0 / 9 | 🟠 Medium |
| **CI/CD Enhancements** | Coverage reports, linting, security scans, and staging deployment pipeline. | ☐ 0 / 4 | 🔴 High |
| **Code Quality** | Pydantic v2 migration, integration tests, contract tests, and benchmarks. | ☐ 0 / 4 | 🟡 Medium |
| **Security & Dependencies** | Dependabot, vulnerability and secrets scanning. | ☐ 0 / 3 | 🔴 High |
| **Auth & Routes** | `/auth/me` verification, contract standardization, status code updates. | ✅ 3 / 4 | 🟢 Complete (minor follow-up) |
| **Testing** | JWT unit tests, integration flow, snapshot fixtures, admin tests. | ☐ 0 / 5 | 🔴 High |
| **Dependabot Remediation** | Package upgrades (`ecdsa`, `starlette`, bcrypt pinning) and upload limits. | ☐ 0 / 3 | 🟠 Medium |
| **DevEx & Observability** | Route prefix validation, add `/auth/me` docs, improve logs. | ☐ 0 / 2 | 🟡 Medium |
| **Schema & Alembic** | Migration validation, test isolation, and debugging logs. | ☐ 0 / 3 | 🟠 Medium |
| **Debugging & Refactor** | Settings attribute fixes, Pydantic deprecation cleanup. | ✅ 1 / 2 | 🟡 Medium |
| **Overall Status** | CI pipeline passing, environment parity confirmed. Ready for advanced automation. | ✅ Stable | 🟢 Ready |

---

## CI/CD Pipeline

### Documentation
- [ ] Add API reference documentation
- [ ] Add OpenAPI schema documentation
- [ ] Add API contract testing documentation
- [ ] Add deployment documentation
- [ ] Add CI/CD documentation
- [ ] Add testing documentation
- [ ] Add security documentation
- [ ] Add development documentation
- [ ] Add deployment documentation

### CI/CD Enhancements
- [ ] Add code coverage reporting with pytest-cov
- [x] Implement linting checks (black, flake8, mypy)
- [ ] Add security scanning with bandit or safety
- [ ] Set up deployment pipeline for staging/production

### Code Quality
- [ ] Continue Pydantic v2 migration across remaining schemas
- [ ] Add more comprehensive integration tests
- [ ] Implement API contract testing
- [ ] Add performance benchmarking to CI

### Security & Dependencies
- [ ] Set up Dependabot for automated dependency updates
- [ ] Add vulnerability scanning to CI pipeline
- [ ] Implement secrets scanning for sensitive data

---

### Next Steps Carryover From Previous Entry

## Auth & Routes
- [X] Verify `/api/v1/auth/me` end-to-end in Insomnia (expect 200 with `{id, username, is_admin}`) after adding `from fastapi import status`.

*The below checklist items were done on 9-1-2025*
- [X] Standardize login contract and update code/docs accordingly: 
  - [X] **Choose one:** JSON payload (`LoginRequest` schema) **or** form (`OAuth2PasswordRequestForm`).
  - [X] Update API docs and Insomnia collections to match the choice.
- [ ] Return **201 Created** for `POST /api/v1/auth/register` (optional, but recommended).

### Testing
- [ ] Add unit tests for JWT:
  - [ ] Expiration handling.
  - [ ] Invalid signature / malformed token.
  - [ ] Missing/empty `sub`.
  - [ ] Revoked/disabled user.
- [ ] Add integration test: login → hit protected route → expect 200; bad token → expect 401.
- [ ] Create **snapshot DB fixtures** for deterministic auth tests.
- [ ] Add `/admin/purge` tests with `get_current_admin` override.

### Security & Dependencies (Dependabot)
- [ ] Remediate alerts:
  - [ ] Upgrade/remove `ecdsa` (python-ecdsa) to a patched version or drop if unused.
  - [ ] Bump `starlette` to a patched release for multipart DoS.
- [ ] Add protections:
  - [ ] Upload size limits (middleware or reverse-proxy) on `/projects/upload`.
  - [ ] Add `pip-audit` or `safety` to CI; fail on critical vulns.
- [ ] (Optional) Pin to quiet bcrypt warning: `passlib[bcrypt]==1.7.4` and `bcrypt>=4.1.2`.

### DevEx & Observability
- [ ] Confirm router prefixes produce exactly `/api/v1/auth/*` (no double `/auth`); assert via route listing in startup logs or `for r in app.routes`.
- [ ] Document `/auth/me` in API reference and include request/response examples.

### 📦 Status

- ✅ **CI Pipeline:** Fully functional with PostgreSQL integration
- ✅ **Tests:** Consistently passing in isolated environment  
- ✅ **Code Quality:** Schema refactoring complete with computed fields
- ✅ **Environment Parity:** Local and CI environments aligned
- 🚀 **Ready for:** Advanced CI features and deployment automation

---

## Auth Flow

### Documentation

### Next Steps

### Auth & Routes
- [X] Verify `/api/v1/auth/me` end-to-end in Insomnia (expect 200 with `{id, username, is_admin}`) after adding `from fastapi import status`.

*The below checklist items were done on 9-1-2025*
- [X] Standardize login contract and update code/docs accordingly: 
  - [X] **Choose one:** JSON payload (`LoginRequest` schema) **or** form (`OAuth2PasswordRequestForm`).
  - [X] Update API docs and Insomnia collections to match the choice.
- [X] Return **201 Created** for `POST /api/v1/auth/register` (optional, but recommended).

### Testing
- [ ] Add unit tests for JWT:
  - [ ] Expiration handling.
  - [ ] Invalid signature / malformed token.
  - [ ] Missing/empty `sub`.
  - [ ] Revoked/disabled user.
- [ ] Add integration test: login → hit protected route → expect 200; bad token → expect 401.
- [ ] Create **snapshot DB fixtures** for deterministic auth tests.
- [ ] Add `/admin/purge` tests with `get_current_admin` override.

### Security & Dependencies (Dependabot)
- [ ] Remediate alerts:
  - [ ] Upgrade/remove `ecdsa` (python-ecdsa) to a patched version or drop if unused.
  - [ ] Bump `starlette` to a patched release for multipart DoS.
- [ ] Add protections:
  - [ ] Upload size limits (middleware or reverse-proxy) on `/projects/upload`.
  - [ ] Add `pip-audit` or `safety` to CI; fail on critical vulns.
- [ ] (Optional) Pin to quiet bcrypt warning: `passlib[bcrypt]==1.7.4` and `bcrypt>=4.1.2`.

### DevEx & Observability
- [ ] Confirm router prefixes produce exactly `/api/v1/auth/*` (no double `/auth`); assert via route listing in startup logs or `for r in app.routes`.
- [ ] Document `/auth/me` in API reference and include request/response examples.

---

## Auth Refactor

### Documentation

### 🔐 Next Steps

- [ ] Implement protected `/me` route using `get_current_user`
- [ ] Add `/admin/purge` test with `get_current_admin` override
- [ ] Start integrating JWT testing (expiration, invalid token, etc.)
- [ ] Add integration test for login → protected route access
- [ ] Snapshot database test fixtures

---

## Schema 

### Documentation


### ✅ Next Steps

### Immediate
- [ ] Run:
  ```bash
  alembic revision --autogenerate -m "initial schema"
  alembic upgrade head
  ```
  (if not already done after confirming tables exist)

- [ ] Review `conftest.py` to:
  - Ensure test DB is used (`TEST_DATABASE_URL`)
  - Add proper teardown and timeout logic for `TestClient`
  - Isolate tests from real development data

### Diagnostic
- [ ] Add logging to `conftest.py` to trace setup/teardown
- [ ] Run:
  ```bash
  pytest tests/ --maxfail=1 -v --capture=no
  ```
  to inspect where the hang occurs

### Strategic
- [ ] Add test DB isolation
- [ ] Add `docs/debugging_alembic.md` to preserve recovery process
- [ ] Begin validating API endpoints again (e.g. `/auth/login`, `/items/search`)

---

### ✅ Next Steps For Our Next Session

✅ Immediately:
- Edit `migrations/env.py`:
  - Delete:
    ```python
    config.file_config._interpolation = None
    ```

✅ Then:
- From project root, run:
  ```bash
  alembic upgrade head
  ```
- Check:
  ```bash
  \dt
  ```
  → confirm tables `projects`, `items`, `users` exist.

✅ After DB is rebuilt:
- Re-run tests:
  ```bash
  pytest tests/test_auth.py -v
  ```
- Confirm purge route no longer hangs.

---

### ✅ Notes

- No need to change alembic.ini beyond keeping:
  ```
  script_location = %(here)s/migrations
  ```
- Leaving `sqlalchemy.url` blank in alembic.ini is fine since env.py overrides it dynamically.
- Current admin security dependency can remain commented out until DB is healthy and tests are passing.

---

## Debugging: Auth, Routes, and Migration

### Documentation

### ❌ Outstanding Issues

### 1. AttributeError in Tests

- Tests currently fail with:
  ```
  AttributeError: 'Settings' object has no attribute 'ACCESS_TOKEN_EXPIRE_MINUTES'
  ```
- **Action needed:**  
  - Update `settings.py` with:
    ```python
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ```
  - Update all references to use:
    ```python
    settings.access_token_expire_minutes
    ```

---

### 2. Pydantic Deprecations

- Still pending:
  - Replace:
    ```python
    Field(..., example="...")
    ```
    → with:
    ```python
    Field(..., json_schema_extra={"example": "..."})
    ```
  - Migrate class `Config` to `ConfigDict` for v3 compatibility.

---

### ✅ Next Steps

✅ Immediate:
- Run test:
  - pytest tests/test_auth.py
- Complete the settings refactor:
  - Add missing attributes.
  - Replace all legacy constant references.

✅ Then:
- Rerun tests:
  ```
  pytest tests/test_auth.py
  ```
- Resolve any final failures.

✅ Future:
- Address Pydantic v2 deprecations.
- Regenerate `requirements.txt` from uv for consistent environments.

---
