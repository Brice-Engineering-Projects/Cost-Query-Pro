---
title: Schema and Migration
date: 2025-07-20
module: Schema and Migration
type: project
tags:
author: Brice Nelson
author_link: https://github.com/Brice-Engineering-Projects/Cost-Query-Pro
status: completed
---

## ✅ Cost Query Pro – Session Summary

### 📦 Status

- ✅ Alembic working
- ✅ DB schema rebuilt
- ✅ Auth tests started
- 🚧 Tests are hanging — needs debug
- 🧠 Dev-level config and migration knowledge leveled up

==========================================================

 Date:  July 20, 2025

=========================================================

## 🔧 What Was Fixed Today

### 1. **Database Was Empty Due to Testing Side Effects**

- All tables were wiped because tests were using the **real dev DB**.
- No Alembic migrations existed to rebuild the schema.

### 2. **Repaired Alembic `env.py`**

- Problem: Alembic failed due to `%40` in password + broken interpolation.
- Fixed by:
  - Removing `config.set_main_option(...)` which triggered interpolation bugs.
  - Switching to:

    ```python
    config.attributes["sqlalchemy.url"] = url
    connectable = create_engine(url, poolclass=pool.NullPool)
    ```

### 3. **Validated SQLAlchemy Connection**

- Created an independent test script to confirm the database URL and credentials were valid.
- Verified the connection string worked directly with SQLAlchemy’s `create_engine`.

### 4. **Confirmed Environment Switching**

- Rewrote the logic in `env.py` to respect `ENVIRONMENT` from `.env`:

  ```python
  if settings.environment == "testing":
      raw_url = settings.test_database_url
  elif settings.environment == "development":
      raw_url = settings.dev_database_url
  else:
      raw_url = settings.database_url

  url = raw_url.unicode_string() if hasattr(raw_url, "unicode_string") else str(raw_url)
  ```

### 5. **Successfully Ran `alembic upgrade head`**

- After fixing `env.py` and validating the DB URL, Alembic successfully recreated the schema.
- You are now back to a clean and working state.

---

## 🚧 Issues Not Yet Resolved

- `pytest` runs appear to **hang** or **run very slowly**, even with only a few tests.
- You had to terminate the process manually with `^C`.
- The root cause may be:
  - `TestClient` holding a hanging thread (seen in traceback)
  - Poor session teardown or a DB connection not closing

---

## ✅ Next Steps

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

## 📦 Status (Jul 2025)

- ✅ Alembic working
- ✅ DB schema rebuilt
- ✅ Auth tests started
- 🚧 Tests are hanging — needs debug
- 🧠 Dev-level config and migration knowledge leveled up

---

Let’s pick back up next session with test teardown diagnostics.

---

==============================================

Date:  July 12, 2025

==============================================

## ✅ Cost Query Pro – Session Summary (Jul 2025)

### ✅ What We Worked On

### 1. Pytest Failing on Auth Settings

- Initial failures:

  ```bash
  AttributeError: 'Settings' object has no attribute 'ACCESS_TOKEN_EXPIRE_MINUTES'
  ```

- Root cause:
  - Code was incorrectly using uppercase attribute names:

    ```python
    settings.ACCESS_TOKEN_EXPIRE_MINUTES
    ```

  - Fixed to:

    ```python
    settings.access_token_expire_minutes
    ```

- Similar corrections for:

  ```python
  settings.SECRET_KEY → settings.secret_key
  settings.ALGORITHM → settings.algorithm
  ```

---

### 2. Purge Endpoint Hanging

- Auth dependency `current_admin` was causing test hangs due to token validation waiting for DB queries.
- Tested commenting out:

  ```python
  current_admin = Depends(get_current_admin)
  ```

- Purge still hung even without auth → problem shifted to DB side.

---

### 3. DB-Level Investigation

- Confirmed tables exist:

  ```text
  projects
  items
  users
  ```

- Discovered:
  - Hanging likely caused by:
    - leftover locks
    - interrupted migrations
    - open transactions from previous sessions

- Noted:
  Killing long-running transactions rolled back DDL, removing tables created in uncommitted migrations.

---

### 4. Alembic Migration Problems

- Ran:

  ```bash
  alembic upgrade head
  ```

- Got crash:

  ```bash
  AttributeError: 'NoneType' object has no attribute 'before_set'
  ```

- Root cause:
  - Code was forcibly setting:

    ```python
    config.file_config._interpolation = None
    ```

    which broke configparser interpolation.

- Confirmed:
  Alembic needs `_interpolation` for:

  ```text
  script_location = %(here)s/migrations
  ```

- Proposed fix:
  - Remove:

    ```python
    config.file_config._interpolation = None
    ```

  - Leave interpolation intact so Alembic can resolve `%(here)s`.

---

## ✅ Where We Left Off

- You **still need to re-run Alembic migrations** to recreate the tables.
- `env.py` needs editing:
  - **Remove**:

    ```python
    config.file_config._interpolation = None
    ```

- Once fixed, run:

  ```bash
  alembic upgrade head
  ```

---

==============================================

Date:  July 9, 2025

==============================================

### Summary of Modifications

1. Migrations
   - Move database URL configuration to settings-based approach
   - Consolidate Base model definition in `db/__init__.py`
   - Restructure migrations for better separation of concerns
   - Update model imports to use consolidated base
   - Split schema migrations into users and other tables

2. Tests
    - Create tests for auth
    - Create tests for routes
    - Create conftest file
