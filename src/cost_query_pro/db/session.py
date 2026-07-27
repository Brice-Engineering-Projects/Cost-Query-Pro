"""src/cost_query_pro/db/session.py"""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from cost_query_pro.config.settings import settings


def _resolve_db_url() -> str:
    # Prefer env (so CI/local tests can override), otherwise settings
    url = os.getenv("DATABASE_URL") or str(settings.database_url or "")
    if not url:
        # last-ditch fallback so imports don't explode in dev
        url = "sqlite:///./dev.db"
    return url


def _safety_check(url: str) -> None:
    """If we're running tests, refuse to touch a non-test DB."""
    if os.getenv("TESTING") == "1":
        u = make_url(url)
        is_local = str(u.host) in {"localhost", "127.0.0.1"}
        is_test_db = str(u.database).endswith("_test")
        if not (is_local and is_test_db):
            raise RuntimeError(f"Refusing to run tests against non-test DB: {u!s}")


DB_URL = _resolve_db_url()
_safety_check(DB_URL)

engine = create_engine(
    DB_URL,
    pool_size=settings.db_pool_size,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    max_overflow=settings.db_max_overflow,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
