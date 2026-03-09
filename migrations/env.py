"""migrations/env.py"""

# ruff: noqa: E402
# flake8: noqa: E402
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from alembic.config import Config
from sqlalchemy import create_engine, pool

test_db_url = os.getenv("TEST_DATABASE_URL")
db_url = os.getenv("DATABASE_URL")

# Ensure Alembic can find `src/cost_query_pro`
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR / "src"))

from cost_query_pro.config.settings import settings

# --- import app modules ---
from cost_query_pro.db import Base

# Load alembic.ini explicitly
config = Config("alembic.ini")

if test_db_url:
    # Escape % for ConfigParser interpolation safety.
    config.set_main_option("sqlalchemy.url", test_db_url.replace("%", "%%"))

# ✅ DO NOT modify _interpolation — this will break Alembic
# config.file_config._interpolation = None  ← REMOVE THIS LINE

# Determine DB URL with explicit env vars taking precedence.
# This keeps CI deterministic even when ENVIRONMENT is not set to "testing".
if test_db_url:
    raw_url = test_db_url
elif db_url:
    raw_url = db_url
elif settings.environment == "testing":
    raw_url = settings.test_database_url
elif settings.environment == "development":
    raw_url = settings.dev_database_url
else:
    raw_url = settings.database_url

# Convert PostgresDsn / URL object to plain string for Alembic.
url = str(raw_url or "").strip()
if not url:
    raise RuntimeError(
        "Alembic DB URL is empty. Set TEST_DATABASE_URL or DATABASE_URL."
    )

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
