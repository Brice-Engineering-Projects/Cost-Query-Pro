---
title: Auth Refactor
date: 2025-08-02
module: Auth Refactor
type: project
tags:
author: Brice Nelson
author_link: https://github.com/Brice-Engineering-Projects/Cost-Query-Pro
status: Completed
---

========================================================

Date:  August 2, 2025

========================================================

# ✅ Cost Query Pro: Auth Refactor & Test Fix Recap (FastAPI + SQLAlchemy)

## 🧩 Problem Summary

After restructuring the project into an `src/` layout, tests were failing with:

```
fastapi.exceptions.FastAPIError: Invalid args for response field!
Hint: check that <class 'src.app.models.user.User'> is a valid Pydantic field type
```

Despite:
- `response_model=UserRead` correctly declared
- `UserRead` being a valid Pydantic model with `orm_mode=True`
- `.pyc` and `__pycache__` cleared
- Imports and routers correctly scoped to `src.app.main`

The issue persisted due to an indirect serialization mismatch.

---

## 🧪 Root Cause

FastAPI’s response system tried to serialize a **SQLAlchemy `User` model instance** using a declared `response_model=UserRead`, but the return value was a hand-built Pydantic instance (`UserRead(id=999, ...)`) used for testing.

This caused FastAPI to validate that `User` is a valid response type (which it isn’t), leading to serialization failure.

---

## 🛠️ Fix Summary

- ✅ Replaced test return `UserRead(...)` with `UserRead.from_orm(new_user)` to match expected serialization flow.
- ✅ Confirmed `UserRead` has `orm_mode = True`.
- ✅ Verified no remaining `response_model=User` or `response_model=DBUser` exist in codebase.
- ✅ Confirmed tests are importing `app` from `src.app.main`, not a stale root `main.py`.

---

## ✅ Final Fix

### `register()` Route

```python
@router.post("/register", response_model=UserRead)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    user_in_db = db.query(DBUser).filter(DBUser.username == user_data.username).first()
    if user_in_db:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_pw = get_password_hash(user_data.password)
    new_user = DBUser(
        username=user_data.username,
        password_hash=hashed_pw,
        is_admin=user_data.is_admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserRead.from_orm(new_user)  # ✅ Proper Pydantic serialization
```

---

## 🧪 Tests: ✅ PASSED

All `pytest` tests now pass cleanly:

```text
$ pytest
tests/test_auth.py ...                             [100%]
```

---
