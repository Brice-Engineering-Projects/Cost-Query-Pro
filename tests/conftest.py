"""tests/conftest.py"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from src.app.main import app
from src.app import Base
from src.app.db.session import get_db
from src.app.config.settings import settings


print("✅ LOADING conftest.py from:", __file__)


# ------------------------------------------------------------
# Validate test DB URL exists
# ------------------------------------------------------------

TEST_DATABASE_URL = str(settings.test_database_url)
assert TEST_DATABASE_URL, "TEST_DATABASE_URL must be set for tests!"

# ------------------------------------------------------------
# Create test DB engine and session factory
# ------------------------------------------------------------

# Create SQLAlchemy engine for the test DB
engine = create_engine(TEST_DATABASE_URL)

# Session factory for the test DB
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ------------------------------------------------------------
# Manage DB schema for tests
# ------------------------------------------------------------

# Drop all tables, then create them once at the start
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    """
    Provides the test DB engine for the session.
    """
    yield engine
    # Drop all tables after all tests complete
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Creates a SQLAlchemy DB session per test function,
    running inside a transaction for isolation.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Yields a FastAPI TestClient with DB overrides in place.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def clean_db(db_session):
    """
    Truncate all tables between tests for clean state.
    """
    tables = ["users", "items", "projects"]
    db_session.execute(
        text(
            f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE;"
        )
    )
    db_session.commit()
