---
title: Auth Flow Stabilization
date: 2025-09-01
module: Auth Flow Stabilization
type: project
tags:
author: Brice Nelson
author_link: https://github.com/Brice-Engineering-Projects/Cost-Query-Pro
status: On-going
---

========================================================

Date:  August 24, 2025 -> Initial
Date:  September 1, 2025 -> Updated checks on the checklist

========================================================

# ✅ Cost Query Pro — Auth Flow Stabilization (FastAPI + Pydantic v2)

## 🧩 Problem Summary

While wiring up the auth flow with Insomnia, a few issues surfaced:

- **404s** on `/login` and `/api/v1/auth/login` due to **router prefix mismatches**.
- **422 Unprocessable Entity** on `POST /api/v1/auth/login` when sending **JSON** to a route expecting **form-encoded** credentials.
- **500 Internal Server Error** on `GET /api/v1/auth/me` from `NameError: status is not defined`.
- Pydantic v2 warning about `orm_mode` and a failure when calling `from_orm(...)` without enabling v2’s `from_attributes`.

---

## 🧪 Root Cause

- **Pydantic v2 change:** `orm_mode=True` → **`model_config = ConfigDict(from_attributes=True)`** is required for v2 models that use attribute-based validation.
- **Routing:** Mixed/duplicated prefixes (`/api/v1` + `/auth`) produced paths that didn’t match Insomnia calls.
- **Payload contract:** The login route accepted **form-data** (`OAuth2PasswordRequestForm`) while the client sent **JSON**.
- **Missing import:** `from fastapi import status` was not imported in `get_current_user`, causing a 500.
- **Noise:** `passlib/bcrypt` version quirk produced a harmless warning.

---

## 🛠️ Fix Summary

- **Pydantic v2**: Updated read schemas to use v2 config.

    ```python
    # src/cost_query_pro/schemas/user.py
    from pydantic import BaseModel, ConfigDict

    class UserRead(BaseModel):
        id: int
        username: str
        is_admin: bool
        model_config = ConfigDict(from_attributes=True)
    ```

    Route code can now use: `UserRead.from_orm(db_user)` **or** `UserRead.model_validate(db_user, from_attributes=True)`.

- **Routing**: Normalized to produce **`/api/v1/auth/*`** exactly (avoid `/auth/auth/*`).

    ```python
    # Option A (recommended)
    # auth.py
    router = APIRouter(prefix="/auth", tags=["auth"])
    # main.py
    app.include_router(auth.router, prefix="/api/v1")
    # → /api/v1/auth/login, /api/v1/auth/me
    ```

- **Login contract**: Resolved 422 by aligning client/server.
  - Short term: Sent **form URL-encoded** creds from Insomnia to match the existing route; or
  - Long term (preferred): Switched login to a **JSON** schema (`LoginRequest`) and updated docs/client accordingly.

- **`/auth/me`**: Implemented and tied to `get_current_user`.

    ```python
    @router.get("/me", response_model=UserRead)
    def read_me(current_user: DBUser = Depends(get_current_user)):
        return UserRead.model_validate(current_user, from_attributes=True)
    ```

- **Import fix**: Added `from fastapi import status` in `src/app/core/security.py`.

- **bcrypt noise**: Not functional; can be silenced later by pinning compatible `passlib[bcrypt]`/`bcrypt` versions.

---

## ✅ Current Results

- **Register:** `POST /api/v1/auth/register` → **200 OK** (works; can return **201 Created** if desired).
- **Login:** After fixing prefix + payload, `POST /api/v1/auth/login` → **200 OK** with JWT.
- **/me:** Implemented; 500 resolved via missing import fix. *(Retest after the import to confirm 200 + user payload.)*

---

## 📎 Notable Code Snippets (finalized)

```python
# auth.py (router + /me)
router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me", response_model=UserRead)
def read_me(current_user: DBUser = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user, from_attributes=True)
```

# security.py (import + oauth2)
from fastapi import Depends, HTTPException, status
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Optional: register returns 201
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(...): ...
