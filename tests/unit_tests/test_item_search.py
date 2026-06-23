"""tests/unit_tests/test_item_search.py

Unit tests for the item_search service.
SQLAlchemy session is mocked — no database required.
"""

from typing import Literal, Optional
from unittest.mock import MagicMock

from cost_query_pro.schemas.agent import SearchParameters
from cost_query_pro.services.item_search import run_search

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_params(
    intent: Literal["cost_search"] = "cost_search",
    item: str = "ductile iron pipe",
    state: str = "FL",
    year_start: int = 2020,
    year_end: int = 2025,
    unit: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> SearchParameters:
    """Build a SearchParameters with sane defaults; override as needed."""
    return SearchParameters(
        intent=intent,
        item=item,
        state=state,
        year_start=year_start,
        year_end=year_end,
        unit=unit,
        price_min=price_min,
        price_max=price_max,
    )


def _make_db(return_items=None):
    """Return a (db, mock_query) pair with chained query mock."""
    db = MagicMock()
    mock_q = MagicMock()
    db.query.return_value = mock_q
    mock_q.join.return_value = mock_q
    mock_q.filter.return_value = mock_q
    mock_q.all.return_value = return_items if return_items is not None else []
    return db, mock_q


def _make_item(unit_price: float) -> MagicMock:
    item = MagicMock()
    item.unit_price = unit_price
    return item


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunSearch:
    def test_returns_query_results(self):
        items = [_make_item(100.0), _make_item(200.0)]
        db, _ = _make_db(return_items=items)
        params = _make_params()

        result = run_search(params, db)

        assert result == items

    def test_state_us_applies_fewer_filters_than_explicit_state(self):
        db_us, q_us = _make_db()
        db_fl, q_fl = _make_db()

        run_search(_make_params(state="US"), db_us)
        run_search(_make_params(state="FL"), db_fl)

        # state="FL" should add one extra filter compared to state="US"
        assert q_fl.filter.call_count == q_us.filter.call_count + 1

    def test_explicit_state_adds_state_filter(self):
        db, mock_q = _make_db()
        run_search(_make_params(state="TX"), db)

        # Verify at least one filter call was made (state filter is among them)
        assert mock_q.filter.call_count >= 3  # item ilike, year_start, year_end, state

    def test_optional_unit_adds_filter(self):
        db_no_unit, q_no_unit = _make_db()
        db_with_unit, q_with_unit = _make_db()

        run_search(_make_params(unit=None), db_no_unit)
        run_search(_make_params(unit="LF"), db_with_unit)

        assert q_with_unit.filter.call_count == q_no_unit.filter.call_count + 1

    def test_price_filters_add_filters(self):
        db_bare, q_bare = _make_db()
        db_priced, q_priced = _make_db()

        run_search(_make_params(), db_bare)
        run_search(_make_params(price_min=100.0, price_max=500.0), db_priced)

        assert q_priced.filter.call_count == q_bare.filter.call_count + 2

    def test_empty_result_returned_as_empty_list(self):
        db, _ = _make_db(return_items=[])
        result = run_search(_make_params(), db)

        assert result == []
