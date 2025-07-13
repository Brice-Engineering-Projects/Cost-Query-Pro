"""migrations/env.py"""
from alembic import context
from alembic.config import Config
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

from app.db import Base
from app.models.user import User
from app.models.project import Project
from app.models.item import Item
from app.config.settings import settings

# Load alembic.ini explicitly
config = Config("alembic.ini")

# turn off interpolation to avoid issues with % signs
if config.file_config is not None:
    config.file_config._interpolation = None

# dynamically set the URL:
if settings.environment == "testing":
    url = str(settings.test_database_url)
elif settings.environment == "development":
    url = str(settings.dev_database_url)
else:
    url = str(settings.database_url)

if config.file_config is not None:
    config.set_main_option("sqlalchemy.url", url)
else:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
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
