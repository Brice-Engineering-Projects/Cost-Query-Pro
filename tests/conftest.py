"""tests/conftest.py"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.config.settings import settings

# Load your test DB URL from .env or settings
TEST_DATABASE_URL = str(settings.test_database_url)

# Create engine for test DB
engine = create_engine(TEST_DATABASE_URL)

# SessionLocal for test transactions
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Drop & recreate all tables once for the entire test run
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency override to ensure your FastAPI app uses test DB
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Provide a shared DB connection for executing raw SQL
@pytest.fixture(scope="session")
def connection():
    conn = engine.connect()
    yield conn
    conn.close()

# Clean the database between each test
@pytest.fixture(scope="function", autouse=True)
def clean_db(connection):
    """
    Truncate all tables to ensure a clean slate before each test.
    """
    tables = ["users", "projects", "items"]
    connection.execute(
        text(
            f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE;"
        )
    )
    connection.commit()

# Provide a DB session directly for tests that need raw inserts
@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Provide a TestClient to call the FastAPI app
@pytest.fixture(scope="function")
def client():
    """
    Returns a TestClient with DB overrides in place.
    """
    return TestClient(app)
