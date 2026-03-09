<!--docs/README_debugging_alembic.md-->

# 🛠️ Alembic Debugging & Migration Recovery Guide

**Project:** Cost Query Pro
**Use Case:** Fixing Alembic issues when the database has been wiped, migrations are broken, or connection strings contain special characters.

---

## 🔍 Problem Summary

During testing, the project database was accidentally **wiped** due to destructive table logic in the test suite. Since no Alembic migrations had been generated, the `alembic upgrade head` command had **nothing to rebuild**, and the app was left without any tables.

Complicating the recovery:

- The database password included special characters (e.g., `@` encoded as `%40`)
- Alembic interpolation failed on the DSN string
- `PostgresDsn` type from Pydantic caused conflicts with SQLAlchemy when passed directly
- Tests were using the **same database** as development, causing unwanted destructive behavior

---

## ✅ What Was Fixed

### ✅ 1. Alembic Interpolation Bug

**Issue:**
Using `config.set_main_option("sqlalchemy.url", url)` with a password that included `%` caused:

```json
{
AttributeError: 'NoneType' object has no attribute 'before_set'
}
```

**Fix:**
Avoid interpolation entirely by setting:

```python
config.attributes["sqlalchemy.url"] = url
```

---

### ✅ 2. Alembic `env.py` Refactor

**Old (fragile):**

```python
config.set_main_option("sqlalchemy.url", url)
connectable = engine_from_config(...)
```

**New (stable):**

```python
from sqlalchemy import create_engine

connectable = create_engine(
    url,
    poolclass=pool.NullPool,
)
```

This bypasses Alembic’s config parser and uses SQLAlchemy directly.

---

### ✅ 3. Dynamic Environment-Safe DB URL

**Problem:** `PostgresDsn` from Pydantic passed a structured object, not a plain string.

**Fix:**

```python
if settings.environment == "testing":
    raw_url = settings.test_database_url
elif settings.environment == "development":
    raw_url = settings.dev_database_url
else:
    raw_url = settings.database_url

# Safe conversion
url = raw_url.unicode_string() if hasattr(raw_url, "unicode_string") else str(raw_url)
```

---

### ✅ 4. Initial Migration Creation

After repairing the connection and config:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

This recreated the `users`, `projects`, and `items` tables from the SQLAlchemy models.

---

### ✅ 5. Isolated Testing Database

**Old behavior:**
Tests were running against the same database as development, leading to data loss.

**Fix:**

- `.env` now includes:

  ```env
  ENVIRONMENT=testing
  TEST_DATABASE_URL=postgresql+psycopg2://brice-nelson:your_encoded_pass@localhost:5432/cost_query_pro_test_db
  ```

- `env.py` respects environment selection:

  ```python
  if settings.environment == "testing":
      url = settings.test_database_url
  ```

---

## 🧪 How to Rebuild Cleanly

1. Ensure `.env` is valid and passwords are URL-encoded.
2. Run:

   ```bash
   alembic revision --autogenerate -m "initial schema"
   alembic upgrade head
   ```

3. To verify:

```bash
   psql cost_query_pro_dev_db
   \dt
```

---

## 🧠 Lessons Learned

- Alembic doesn’t like `%` signs in URLs unless passed through `config.attributes`
- SQLAlchemy is stricter when receiving structured `PostgresDsn` objects — cast to `str`
- `create_engine(url)` is safer than `engine_from_config()` for dynamic settings
- Testing should **never** use the same database as dev
- A wiped DB is recoverable as long as models and migrations exist

---

## 🏁 Next Steps

- Safely run migrations across dev, test, and production
- Avoid Alembic edge cases
- Rebuild your database structure cleanly using only migrations
- Scale your app with proper testing isolation
