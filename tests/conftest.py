"""tests/conftest.py"""

# flake8: noqa: E402
import os
import sys

# -----------------------------------------------------------
# SET ENVIRONMENT VARIABLES FIRST, before any imports!
# -----------------------------------------------------------
# Guarantee correct DB inside GitHub Actions AND local CLI
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@postgres:5432/test_db"
)

os.environ["ENVIRONMENT"] = "testing"
os.environ["ALLOW_ADMIN_SIGNUP"] = "true"  # Enable admin signup for tests

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

# Alembic (build schema via migrations once per session)
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient

# SQLAlchemy
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from cost_query_pro.config.settings import settings
from cost_query_pro.db.session import get_db

# App imports
from cost_query_pro.main import app

# ------------------------------------------------------------
# Loading banner
# ------------------------------------------------------------
print("✅ LOADING conftest.py from:", __file__)

# ------------------------------------------------------------
# Validate test DB URL exists
# ------------------------------------------------------------
TEST_DATABASE_URL = str(settings.test_database_url)
assert TEST_DATABASE_URL, "TEST_DATABASE_URL must be set for tests!"


# ------------------------------------------------------------
# Create test DB engine and session factory
# ------------------------------------------------------------
# Create SQLAlchemy engine for the test DB (Postgres).
# pool_pre_ping adds resiliency in CI.
engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

# Session factory for the test DB
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ------------------------------------------------------------
# Manage DB schema for tests (Use Alembic migrations once)
# ------------------------------------------------------------
def _run_alembic_upgrades():
    """
    Run Alembic migrations to 'head' against the TEST_DATABASE_URL.
    NOTE: If your alembic.ini is NOT at repo root, adjust the path below.
    """
    alembic_cfg = AlembicConfig("alembic.ini")
    # Force Alembic to use the TEST DB url instead of whatever is in alembic.ini
    # Escape % as %% for ConfigParser (which interprets % as interpolation syntax)
    escaped_url = TEST_DATABASE_URL.replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", escaped_url)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def _migrate_schema_once():
    """
    Build schema ONCE for the whole test session using Alembic.
    We DO NOT downgrade after; test DBs are disposable.
    """
    _run_alembic_upgrades()
    yield
    # Optional cleanup: leave DB as-is. Uncomment if you really need to drop.
    # from sqlalchemy import text
    # with engine.connect() as conn:
    #     conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    #     conn.commit()


# ------------------------------------------------------------
# Per-test DB session isolation (Transaction + savepoint pattern)
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session():
    """
    Creates a SQLAlchemy DB session per test function, running inside a
    top-level transaction + nested SAVEPOINT for isolation.

    WHY this pattern:
    - Your app code may call session.commit(); a plain rollback at the end
      would NOT undo those commits.
    - Using an outer transaction + a nested transaction (SAVEPOINT) means
      app-level commits are contained, and we can still roll everything back
      after each test without TRUNCATE or DROP/CREATE.
    """
    # Open a dedicated connection for this test
    connection = engine.connect()

    # Start a top-level transaction (contains the whole test)
    outer_tx = connection.begin()

    # Bind a session to that connection
    session = TestingSessionLocal(bind=connection)

    # Each time the nested transaction ends (e.g., after a commit),
    # automatically reopen it, so the next commit is contained too.
    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        # Only restart if the connection is still in a transaction
        if sess.is_active and not sess.in_transaction():
            try:
                sess.begin_nested()
            except Exception:
                # Ignore errors during teardown or invalidation
                pass

    # Start a nested transaction (SAVEPOINT) so app-level commits are safe
    session.begin_nested()

    try:
        yield session
    finally:
        # Close session and rollback outer transaction → pristine DB
        session.close()
        outer_tx.rollback()
        connection.close()


# ------------------------------------------------------------
# FastAPI TestClient (Use the per-test session)
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def client(db_session):
    """
    Yields a FastAPI TestClient with DB overrides in place.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            # No explicit close here; db_session fixture handles it.
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency overrides
    app.dependency_overrides.clear()
