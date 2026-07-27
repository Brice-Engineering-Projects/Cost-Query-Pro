"""tests/unit_tests/test_analytics.py

Unit tests for the analytics service.
Pure Python — no database or external dependencies required.
"""

from unittest.mock import MagicMock

import pytest

from cost_query_pro.core.errors import AppError
from cost_query_pro.schemas.agent import CostSummary
from cost_query_pro.services.analytics import compute_summary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(unit_price: float) -> MagicMock:
    item = MagicMock()
    item.unit_price = unit_price
    return item


def _items(*prices: float) -> list:
    return [_make_item(p) for p in prices]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestComputeSummary:
    def test_returns_cost_summary_type(self):
        result = compute_summary(_items(100.0, 200.0, 300.0))
        assert isinstance(result, CostSummary)

    def test_record_count(self):
        result = compute_summary(_items(10.0, 20.0, 30.0, 40.0))
        assert result.record_count == 4

    def test_minimum_and_maximum_price(self):
        result = compute_summary(_items(50.0, 200.0, 150.0, 100.0))
        assert result.minimum_price == 50.0
        assert result.maximum_price == 200.0

    def test_average_price(self):
        result = compute_summary(_items(100.0, 200.0, 300.0))
        assert result.average_price == pytest.approx(200.0)

    def test_median_odd_count(self):
        # Median of [100, 200, 300] = 200
        result = compute_summary(_items(100.0, 300.0, 200.0))
        assert result.median_price == pytest.approx(200.0)

    def test_median_even_count(self):
        # Median of [100, 200, 300, 400] = (200+300)/2 = 250
        result = compute_summary(_items(100.0, 200.0, 300.0, 400.0))
        assert result.median_price == pytest.approx(250.0)

    def test_single_item(self):
        result = compute_summary(_items(99.99))
        assert result.record_count == 1
        assert result.median_price == pytest.approx(99.99)
        assert result.average_price == pytest.approx(99.99)
        assert result.minimum_price == pytest.approx(99.99)
        assert result.maximum_price == pytest.approx(99.99)

    def test_all_same_price(self):
        result = compute_summary(_items(150.0, 150.0, 150.0))
        assert result.median_price == pytest.approx(150.0)
        assert result.average_price == pytest.approx(150.0)
        assert result.minimum_price == pytest.approx(150.0)
        assert result.maximum_price == pytest.approx(150.0)

    def test_empty_list_raises_app_error(self):
        with pytest.raises(AppError) as exc_info:
            compute_summary([])

        assert exc_info.value.code == "NO_RESULTS"
        assert exc_info.value.status_code == 404

    def test_empty_list_error_message_is_helpful(self):
        with pytest.raises(AppError) as exc_info:
            compute_summary([])

        assert "No matching records" in exc_info.value.message
