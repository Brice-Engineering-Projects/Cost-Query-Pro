from logging.config import fileConfig
import sys
import os

from sqlalchemy import create_engine, pool
from alembic import context
from app.db import Base
import app.models




# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import app models and Base metadata
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db import Base
from app import models
from app.config.settings import settings

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    from app.config.settings import settings
    url = str(settings.database_url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()



def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = create_engine(
        str(settings.database_url),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
