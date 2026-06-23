"""src/cost_query_pro/services/item_search.py

Step 2 of the Secure Query Pipeline: translate SearchParameters into a
database query. The LLM has no access to this module or the database.
"""

import logging

from sqlalchemy.orm import Session

from cost_query_pro.models import Item, Project
from cost_query_pro.schemas.agent import SearchParameters

logger = logging.getLogger(__name__)


def run_search(params: SearchParameters, db: Session) -> list[Item]:
    """Execute a database search from validated SearchParameters.

    A single JOIN on Item.project covers all project-level filters
    (state, year range), avoiding the double-join pattern in the
    existing items.py search endpoint.

    Args:
        params: Validated SearchParameters from the intent parser.
        db: SQLAlchemy session.

    Returns:
        List of matching Item ORM objects (may be empty).
    """
    query = (
        db.query(Item)
        .join(Item.project)
        .filter(Item.item_description.ilike(f"%{params.item}%"))
        .filter(Project.year >= params.year_start)
        .filter(Project.year <= params.year_end)
    )

    # "US" is the intent parser's placeholder when no state was mentioned
    if params.state != "US":
        query = query.filter(Project.state == params.state)

    if params.unit:
        query = query.filter(Item.unit.ilike(f"%{params.unit}%"))
    if params.price_min is not None:
        query = query.filter(Item.unit_price >= params.price_min)
    if params.price_max is not None:
        query = query.filter(Item.unit_price <= params.price_max)

    results = query.all()
    logger.debug(
        "run_search returned %d items for item=%r state=%r years=%s-%s",
        len(results),
        params.item,
        params.state,
        params.year_start,
        params.year_end,
    )
    return results
