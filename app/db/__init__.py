"""app/db/__init__.py"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config.settings import settings

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

Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
