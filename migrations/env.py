"""migrations/env.py"""
from alembic import context
from alembic.config import Config
from sqlalchemy import engine_from_config, pool, create_engine
from logging.config import fileConfig

from app.db import Base
from app.models.user import User
from app.models.project import Project
from app.models.item import Item
from app.config.settings import settings

# Load alembic.ini explicitly
config = Config("alembic.ini")

# ✅ DO NOT modify _interpolation — this will break Alembic
# config.file_config._interpolation = None  ← REMOVE THIS LINE

# Determine DB URL based on current environment
if settings.environment == "testing":
    raw_url = settings.test_database_url
elif settings.environment == "development":
    raw_url = settings.dev_database_url
else:
    raw_url = settings.database_url

# Convert PostgresDsn to plain string for Alembic
url = str(raw_url)


# ✅ Use config.attributes to safely inject raw DB URL
config.attributes["sqlalchemy.url"] = url

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
