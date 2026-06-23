"""src/cost_query_pro/services/agent_tools.py

Anthropic/OpenAI-compatible tool definitions and backend handler functions
for the Cost Query Pro agent.

Each tool definition follows the Anthropic function-calling specification:
  { "name": str, "description": str, "input_schema": { "type": "object", ... } }

Handler functions implement each tool using existing service infrastructure
(run_search, compute_summary) and return Pydantic model instances that are
safe to serialize to the LLM.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from cost_query_pro.core.errors import AppError
from cost_query_pro.models import Item, Project
from cost_query_pro.schemas.agent import (
    CostSummary,
    ProjectSummary,
    SearchParameters,
)
from cost_query_pro.services.analytics import compute_summary
from cost_query_pro.services.item_search import run_search

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool Schema Definitions (Anthropic function-calling format)
# ---------------------------------------------------------------------------

KEYWORD_SEARCH_TOOL = {
    "name": "keyword_search",
    "description": (
        "Search construction cost records by item description keyword. "
        "Returns aggregate price statistics (record count, median, average, min, max). "
        "Use for broad searches when state and year range are not critical."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Search term for item description (e.g. 'ductile iron pipe').",
            },
            "state": {
                "type": "string",
                "description": "Two-letter US state code to restrict results. Omit for all states.",
            },
            "year_start": {"type": "integer", "description": "Start year (inclusive)."},
            "year_end": {"type": "integer", "description": "End year (inclusive)."},
        },
        "required": ["keyword"],
    },
}

FILTER_SEARCH_TOOL = {
    "name": "filter_search",
    "description": (
        "Search with explicit state and year range filters. "
        "Returns aggregate price statistics. "
        "Use when the user specifies a geography and time window."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "Item description keyword."},
            "state": {"type": "string", "description": "Two-letter US state code."},
            "year_start": {"type": "integer", "description": "Start year (inclusive)."},
            "year_end": {"type": "integer", "description": "End year (inclusive)."},
            "unit": {
                "type": "string",
                "description": "Unit of measure (e.g. 'LF', 'EA').",
            },
            "price_min": {
                "type": "number",
                "description": "Minimum unit price filter.",
            },
            "price_max": {
                "type": "number",
                "description": "Maximum unit price filter.",
            },
        },
        "required": ["keyword", "state", "year_start", "year_end"],
    },
}

PRICE_STATS_TOOL = {
    "name": "price_stats",
    "description": (
        "Retrieve pricing statistics for a specific item description. "
        "Returns record count, median, average, min, and max unit price. "
        "Use when the user asks 'what does X cost?'"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "item_description": {
                "type": "string",
                "description": "Item description to look up.",
            },
            "state": {
                "type": "string",
                "description": "Two-letter US state code. Omit for all states.",
            },
            "year_start": {"type": "integer", "description": "Start year."},
            "year_end": {"type": "integer", "description": "End year."},
        },
        "required": ["item_description"],
    },
}

PROJECT_LOOKUP_TOOL = {
    "name": "project_lookup",
    "description": (
        "Look up how many projects have used a given item, covering which years "
        "and states. Returns project count, year range, and list of state codes. "
        "Use when the user asks about market presence, geographic reach, or 'how common is X?'"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "Item description keyword."},
        },
        "required": ["keyword"],
    },
}

ALL_TOOLS = [
    KEYWORD_SEARCH_TOOL,
    FILTER_SEARCH_TOOL,
    PRICE_STATS_TOOL,
    PROJECT_LOOKUP_TOOL,
]

# ---------------------------------------------------------------------------
# Sentinel defaults for optional year/state inputs
# ---------------------------------------------------------------------------

_DEFAULT_YEAR_START = 1900
_DEFAULT_YEAR_END = 2100
_DEFAULT_STATE = "US"  # "US" = all states in run_search


def _build_params(
    item: str,
    state: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    unit: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> SearchParameters:
    """Construct SearchParameters with safe defaults for missing optional inputs."""
    return SearchParameters(
        intent="cost_search",
        item=item,
        state=state if state else _DEFAULT_STATE,
        year_start=year_start if year_start is not None else _DEFAULT_YEAR_START,
        year_end=year_end if year_end is not None else _DEFAULT_YEAR_END,
        unit=unit,
        price_min=price_min,
        price_max=price_max,
    )


# ---------------------------------------------------------------------------
# Handler Functions
# ---------------------------------------------------------------------------


def handle_keyword_search(
    db: Session,
    keyword: str,
    state: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
) -> CostSummary:
    """Broad keyword search — state and year range are optional."""
    params = _build_params(
        item=keyword, state=state, year_start=year_start, year_end=year_end
    )
    items = run_search(params, db)
    return compute_summary(items)


def handle_filter_search(
    db: Session,
    keyword: str,
    state: str,
    year_start: int,
    year_end: int,
    unit: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> CostSummary:
    """Targeted search with required state and year range."""
    params = _build_params(
        item=keyword,
        state=state,
        year_start=year_start,
        year_end=year_end,
        unit=unit,
        price_min=price_min,
        price_max=price_max,
    )
    items = run_search(params, db)
    return compute_summary(items)


def handle_price_stats(
    db: Session,
    item_description: str,
    state: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
) -> CostSummary:
    """Pricing statistics for a specific item description."""
    params = _build_params(
        item=item_description,
        state=state,
        year_start=year_start,
        year_end=year_end,
    )
    items = run_search(params, db)
    return compute_summary(items)


def handle_project_lookup(db: Session, keyword: str) -> ProjectSummary:
    """Project-level metadata for items matching a keyword.

    Returns project count, year range, and distinct states without
    exposing individual project records.
    """
    projects = (
        db.query(Project)
        .join(Project.items)
        .filter(Item.item_description.ilike(f"%{keyword}%"))
        .distinct()
        .all()
    )

    if not projects:
        raise AppError(
            "NO_RESULTS",
            f"No projects found with items matching '{keyword}'.",
            404,
        )

    return ProjectSummary(
        project_count=len(projects),
        year_min=min(p.year for p in projects),
        year_max=max(p.year for p in projects),
        states=sorted({p.state for p in projects}),
    )


# ---------------------------------------------------------------------------
# Tool Dispatcher
# ---------------------------------------------------------------------------


def execute_tool(tool_name: str, tool_input: dict, db: Session) -> dict:
    """Route a tool call by name to its backend handler.

    Args:
        tool_name: One of 'keyword_search', 'filter_search', 'price_stats',
                   'project_lookup'.
        tool_input: Dict of keyword arguments for the named handler.
        db: SQLAlchemy session.

    Returns:
        JSON-serializable dict (model_dump of the handler's Pydantic result).

    Raises:
        AppError: code='UNKNOWN_TOOL', status=400 for unrecognised tool names.
        AppError: code='NO_RESULTS', status=404 if no records match the query.
    """
    if tool_name not in _HANDLERS:
        raise AppError("UNKNOWN_TOOL", f"No tool named '{tool_name}'.", 400)

    result = _HANDLERS[tool_name](db, **tool_input)
    return result.model_dump()


# Map after functions are defined
_HANDLERS = {
    "keyword_search": handle_keyword_search,
    "filter_search": handle_filter_search,
    "price_stats": handle_price_stats,
    "project_lookup": handle_project_lookup,
}
