# Diary Logs


========================================================

Date: September 8, 2025

========================================================

# ✅ Cost Query Pro — GitHub Actions CI/CD Pipeline Setup & Green Tests

## 🧩 Problem Summary

Setting up a robust CI/CD pipeline for the FastAPI project with proper test isolation and dependency management. Initial challenges included:

- **Test environment isolation** - ensuring CI tests don't interfere with local development
- **Database setup** - configuring PostgreSQL service for CI testing
- **Dependency management** - ensuring consistent package versions between local and CI
- **Schema refactoring** - modernizing Pydantic models for better maintainability
- **Test reliability** - achieving consistent passing tests across environments

---

## 🧪 CI/CD Pipeline Implementation

### 1. **GitHub Actions Workflow Setup**
- Created `.github/workflows/ci.yml` with:
  - **Python 3.12** environment matching local development
  - **PostgreSQL 13** service container for database tests
  - **Environment variables** for test database configuration
  - **Multi-step process:** install dependencies → run migrations → execute tests

### 2. **Database Service Configuration**
- Configured PostgreSQL service in GitHub Actions:
  ```yaml
  services:
    postgres:
      image: postgres:13
      env:
        POSTGRES_PASSWORD: testpass
        POSTGRES_USER: testuser
        POSTGRES_DB: testdb
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  ```

### 3. **Environment Variable Management**
- Set up CI-specific environment variables:
  - `TEST_DATABASE_URL` for isolated test database
  - `SECRET_KEY` for JWT token generation
  - `ENVIRONMENT=testing` to ensure proper config loading

### 4. **Migration Integration**
- Added Alembic migration step to CI pipeline:
  ```yaml
  - name: Run database migrations
    run: |
      alembic upgrade head
    env:
      DATABASE_URL: ${{ env.TEST_DATABASE_URL }}
  ```

---

## 🛠️ Code Quality Improvements

### 1. **Schema Refactoring - ItemWithProject**
- **Problem:** Complex field validators duplicating project data
- **Solution:** Replaced with Pydantic `@computed_field` properties
- **Benefits:**
  - Eliminated duplicated validation logic
  - Clearer relationship between project object and derived fields
  - Better maintainability with single source of truth
  - Preserved API compatibility

### 2. **Test Environment Isolation**
- Enhanced `conftest.py` with proper test database setup
- Ensured tests use isolated test database, not development DB
- Added proper cleanup and teardown mechanisms

### 3. **Dependency Consistency**
- Verified `pyproject.toml` and `requirements.txt` alignment
- Ensured all test dependencies are properly declared
- Confirmed Python version consistency (3.12.2)

---

## ✅ Current Results

- **GitHub Actions CI:** ✅ **PASSING** - all tests execute successfully
- **Test Isolation:** ✅ Tests run against dedicated PostgreSQL service
- **Database Migrations:** ✅ Alembic migrations run automatically in CI
- **Code Quality:** ✅ Schema refactoring improves maintainability
- **Environment Parity:** ✅ CI environment matches local development

---

## 📎 Key Achievements

**GitHub Actions Workflow Setup:**
- Install dependencies with pip requirements
- Run database migrations with alembic upgrade head  
- Execute tests with pytest -v --tb=short

**Schema Refactoring Example:**
- Replaced complex validators with @computed_field properties
- Added proper null checking for optional relationships
- Maintained backward API compatibility

---

## 🔧 Technical Lessons Learned

### 1. **CI Database Services**
- PostgreSQL health checks are crucial for reliable test execution
- Service containers need proper environment variable configuration
- Database initialization must complete before migration steps

### 2. **Pydantic Best Practices**
- @computed_field is preferred over complex validators for derived data
- Properties provide cleaner API while maintaining backward compatibility
- Null checking is essential when dealing with optional relationships

### 3. **Environment Management**
- Separate test database URLs prevent CI/local environment conflicts
- Environment-specific settings enable proper test isolation
- Consistent Python versions across environments reduce debugging time

---

## 📋 Next Steps

### CI/CD Enhancements
- [ ] Add code coverage reporting with pytest-cov
- [ ] Implement linting checks (black, flake8, mypy)
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

## Next Steps Carryover From Previous Entry

### Auth & Routes
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

## 📦 Status

- ✅ **CI Pipeline:** Fully functional with PostgreSQL integration
- ✅ **Tests:** Consistently passing in isolated environment  
- ✅ **Code Quality:** Schema refactoring complete with computed fields
- ✅ **Environment Parity:** Local and CI environments aligned
- 🚀 **Ready for:** Advanced CI features and deployment automation

**Status:** 🎯 Solid foundation established for continuous integration and deployment. Pipeline is reliable and ready for team collaboration.



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
    # src/app/schemas/user.py
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

## Next Steps

### Auth & Routes
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

```
tests/test_auth.py ...                             [100%]
```

---

## 🔐 Next Steps

- [ ] Implement protected `/me` route using `get_current_user`
- [ ] Add `/admin/purge` test with `get_current_admin` override
- [ ] Start integrating JWT testing (expiration, invalid token, etc.)
- [ ] Add integration test for login → protected route access
- [ ] Snapshot database test fixtures

---

**Status:** ✅ Auth system is stable and testable. Refactor complete. Ready to build out the rest of the API.



==========================================================

 Date:  July 20, 2025

=========================================================

# ✅ Cost Query Pro – Session Summary

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

## 📦 Status

- ✅ Alembic working
- ✅ DB schema rebuilt
- ✅ Auth tests started
- 🚧 Tests are hanging — needs debug
- 🧠 Dev-level config and migration knowledge leveled up

---

Let’s pick back up next session with test teardown diagnostics.



==============================================

Date:  July 12, 2025

==============================================

# ✅ Cost Query Pro – Session Summary

## ✅ What We Worked On

### 1. Pytest Failing on Auth Settings
- Initial failures:
  ```
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
  ```
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
  ```
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
  ```
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

## ✅ Next Steps For Our Next Session

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

## ✅ Notes

- No need to change alembic.ini beyond keeping:
  ```
  script_location = %(here)s/migrations
  ```
- Leaving `sqlalchemy.url` blank in alembic.ini is fine since env.py overrides it dynamically.
- Current admin security dependency can remain commented out until DB is healthy and tests are passing.

---

**Status:**  
→ We’re paused until Alembic migrations are fixed and DB is rebuilt.


==============================================

Date:  July 11, 2025

==============================================


# ✅ Cost Query Pro — Debugging & Refactor Session Summary

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

## ✅ Next Steps

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

# ⏸️ Pausing Here

✅ All critical architecture fixes are in place.  
🔧 Remaining task is to fix the missing settings attribute and re-run tests.  
🎯 Close to green tests!

Let’s resume from here when you return!




==============================================

Date:  July 9, 2025

==============================================

### Summary of Modifications

1. Migrations
   - Move database URL configuration to settings-based approach
   - Consolidate Base model definition in db/__init__.py
   - Restructure migrations for better separation of concerns
   - Update model imports to use consolidated base
   - Split schema migrations into users and other tables

2. Tests
    - Create tests for auth
    - Create tests for routes
    - Create conftest file

# Next Task
    - Run pytest
    - Debug errors
