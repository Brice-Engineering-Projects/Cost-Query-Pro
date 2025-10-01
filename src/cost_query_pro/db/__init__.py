"""src/cost_query_pro/db/__init__.py"""

# Use the recommended import path for SQLAlchemy 2.0+
from sqlalchemy.orm import declarative_base

# Create a base class for all SQLAlchemy models
Base = declarative_base()

# Export Base to be imported elsewhere
__all__ = ["Base"]

# Import the get_db function from session.py here to avoid circular imports
from src.cost_query_pro.db.session import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.cost_query_pro.config.settings import settings

if settings.environment == "testing":
    db_url = settings.test_database_url
elif settings.environment == "development":
    db_url = settings.dev_database_url
else:
    db_url = settings.database_url

if db_url is None:
    raise ValueError(
        f"No database URL configured for environment: {settings.environment}"
    )

engine = create_engine(str(db_url))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



