---
title: Debugging with Auth, Routes, and Migrations
date: 2025-07-11
module: Auth, Routes, Migrations
type: project
tags:
author: Brice Nelson
author_link: https://github.com/Brice-Engineering-Projects/Cost-Query-Pro
status: completed
---

==============================================

Date:  July 11, 2025

==============================================

## ✅ Cost Query Pro — Debugging & Refactor Session Summary

## 🎯 Work Completed

### 🔗 Router Fixes

- Identified missing route inclusion in `main.py`.
- Added proper router registrations:

  ```python
  app.include_router(auth.router)
  app.include_router(admin.router)
  app.include_router(projects.router)
  app.include_router(items.router)
  ```

- Confirmed presence of API paths in Swagger UI.
- Fixed duplicate prefix issues in router inclusion.

---

### 🔐 Auth Route Prefixes

- Discovered 404 errors caused by missing prefixes.
- Updated `auth.py` router:

  ```python
  router = APIRouter(
      prefix="/api/v1/auth",
      tags=["auth"]
  )
  ```

- Ensured routes like `/api/v1/auth/register` and `/api/v1/auth/login` exist.

---

### ⚙️ Security Module

- Removed placeholder code:

  ```python
  expire = datetime.now(UTC) + timedelta(...)
  ```

- Implemented proper token expiry:

  ```python
  expire = datetime.now(UTC) + (
      expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
  )
  ```

- Switched from `datetime.utcnow()` to `datetime.now(UTC)` to resolve deprecation warnings.

---

### ⚙️ Settings Refactor

- Discovered missing `ACCESS_TOKEN_EXPIRE_MINUTES` attribute.
- Refactored `settings.py`:
  - Moved all auth config into `Settings` class.
  - Deleted redundant top-level constants.
- Final settings example:

  ```python
  access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
  algorithm: str = Field("HS256", env="ALGORITHM")
  ```

---

### ⚠️ Pydantic Deprecation Warnings

- Noted deprecations in Pydantic v2:
  - `Field(..., example="value")` deprecated.
  - Class-based `Config` is deprecated in favor of `ConfigDict`.
- Deferred these changes for after critical test fixes.

---

## ❌ Outstanding Issues

### 1. AttributeError in Tests

- Tests currently fail with:

  ```bash
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

## ✅ Next Steps

✅ Immediate:

- Run test:
  - pytest tests/test_auth.py
- Complete the settings refactor:
  - Add missing attributes.
  - Replace all legacy constant references.

✅ Then:

- Rerun tests:

  ```bash
  pytest tests/test_auth.py
  ```

- Resolve any final failures.

✅ Future:

- Address Pydantic v2 deprecations.
- Regenerate `uv.lock` with uv for consistent environments.

---

_**⏸️ Pausing Here**_

✅ All critical architecture fixes are in place.
🔧 Remaining task is to fix the missing settings attribute and re-run tests.
🎯 Close to green tests!
