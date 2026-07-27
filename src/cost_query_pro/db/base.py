"""src/cost_query_pro/db/base.py"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every ORM model.

    Declared as a class rather than via ``declarative_base()`` so that type
    checkers see a real base class instead of ``Any``. The runtime contract is
    unchanged: ``Base.metadata`` is still the single MetaData that Alembic
    autogenerate targets in ``migrations/env.py``.
    """
