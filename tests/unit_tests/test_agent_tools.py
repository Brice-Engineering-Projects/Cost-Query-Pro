"""tests/unit_tests/test_agent_tools.py

Unit tests for the agent_tools service.
Pure Python — all database interactions are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from cost_query_pro.core.errors import AppError
from cost_query_pro.schemas.agent import CostSummary, ProjectSummary
from cost_query_pro.services.agent_tools import (
    ALL_TOOLS,
    FILTER_SEARCH_TOOL,
    KEYWORD_SEARCH_TOOL,
    PRICE_STATS_TOOL,
    PROJECT_LOOKUP_TOOL,
    execute_tool,
    handle_filter_search,
    handle_keyword_search,
    handle_price_stats,
    handle_project_lookup,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOOL_LIST = [
    KEYWORD_SEARCH_TOOL,
    FILTER_SEARCH_TOOL,
    PRICE_STATS_TOOL,
    PROJECT_LOOKUP_TOOL,
]

_COST_SUMMARY = CostSummary(
    record_count=5,
    median_price=100.0,
    average_price=110.0,
    minimum_price=80.0,
    maximum_price=150.0,
)


def _make_db():
    return MagicMock()


def _make_project(year: int = 2020, state: str = "FL") -> MagicMock:
    p = MagicMock()
    p.year = year
    p.state = state
    return p


# ---------------------------------------------------------------------------
# Tool Schema Tests
# ---------------------------------------------------------------------------


class TestToolSchemas:
    def test_all_tools_have_required_schema_fields(self):
        for tool in _TOOL_LIST:
            assert "name" in tool, f"Missing 'name' in {tool}"
            assert "description" in tool, f"Missing 'description' in {tool}"
            assert "input_schema" in tool, f"Missing 'input_schema' in {tool}"

    def test_input_schemas_are_valid_objects(self):
        for tool in _TOOL_LIST:
            schema = tool["input_schema"]
            assert (
                schema["type"] == "object"
            ), f"{tool['name']} input_schema type must be 'object'"
            assert (
                "properties" in schema
            ), f"{tool['name']} input_schema missing 'properties'"

    def test_all_tools_have_required_fields_list(self):
        for tool in _TOOL_LIST:
            schema = tool["input_schema"]
            assert (
                "required" in schema
            ), f"{tool['name']} input_schema missing 'required'"
            assert isinstance(
                schema["required"], list
            ), f"{tool['name']} 'required' must be a list"

    def test_all_tools_list_is_complete(self):
        assert len(ALL_TOOLS) == 4
        names = {t["name"] for t in ALL_TOOLS}
        assert names == {
            "keyword_search",
            "filter_search",
            "price_stats",
            "project_lookup",
        }


# ---------------------------------------------------------------------------
# Handler Tests
# ---------------------------------------------------------------------------


class TestHandleKeywordSearch:
    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_returns_cost_summary(self, mock_search, mock_summary):
        db = _make_db()
        result = handle_keyword_search(db, keyword="ductile iron pipe")
        assert isinstance(result, CostSummary)
        assert result.record_count == 5

    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_passes_keyword_to_search(self, mock_search, mock_summary):
        db = _make_db()
        handle_keyword_search(db, keyword="pipe")
        call_params = mock_search.call_args[0][0]
        assert call_params.item == "pipe"

    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_uses_sentinel_defaults_when_no_optional_args(
        self, mock_search, mock_summary
    ):
        db = _make_db()
        handle_keyword_search(db, keyword="pipe")
        params = mock_search.call_args[0][0]
        assert params.state == "US"
        assert params.year_start == 1900
        assert params.year_end == 2100


class TestHandleFilterSearch:
    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_returns_cost_summary(self, mock_search, mock_summary):
        db = _make_db()
        result = handle_filter_search(
            db, keyword="pipe", state="FL", year_start=2018, year_end=2023
        )
        assert isinstance(result, CostSummary)

    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_passes_all_filters_to_search(self, mock_search, mock_summary):
        db = _make_db()
        handle_filter_search(
            db,
            keyword="valve",
            state="TX",
            year_start=2015,
            year_end=2020,
            unit="EA",
            price_min=50.0,
            price_max=500.0,
        )
        params = mock_search.call_args[0][0]
        assert params.item == "valve"
        assert params.state == "TX"
        assert params.year_start == 2015
        assert params.year_end == 2020
        assert params.unit == "EA"
        assert params.price_min == 50.0
        assert params.price_max == 500.0


class TestHandlePriceStats:
    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_returns_cost_summary(self, mock_search, mock_summary):
        db = _make_db()
        result = handle_price_stats(db, item_description="24-inch DIP")
        assert isinstance(result, CostSummary)

    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_passes_item_description_as_item(self, mock_search, mock_summary):
        db = _make_db()
        handle_price_stats(db, item_description="gate valve")
        params = mock_search.call_args[0][0]
        assert params.item == "gate valve"


class TestHandleProjectLookup:
    def test_returns_project_summary(self):
        db = _make_db()
        projects = [
            _make_project(2019, "FL"),
            _make_project(2021, "TX"),
            _make_project(2020, "FL"),
        ]
        db.query.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = (
            projects
        )

        result = handle_project_lookup(db, keyword="pipe")

        assert isinstance(result, ProjectSummary)
        assert result.project_count == 3
        assert result.year_min == 2019
        assert result.year_max == 2021
        assert sorted(result.states) == ["FL", "TX"]

    def test_no_results_raises_app_error(self):
        db = _make_db()
        db.query.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = (
            []
        )

        with pytest.raises(AppError) as exc_info:
            handle_project_lookup(db, keyword="nonexistent item")

        assert exc_info.value.code == "NO_RESULTS"
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Dispatcher Tests
# ---------------------------------------------------------------------------


class TestExecuteTool:
    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_dispatches_keyword_search(self, mock_search, mock_summary):
        db = _make_db()
        result = execute_tool("keyword_search", {"keyword": "pipe"}, db)
        assert isinstance(result, dict)
        assert "record_count" in result
        assert result["record_count"] == 5

    def test_unknown_tool_raises_app_error(self):
        db = _make_db()
        with pytest.raises(AppError) as exc_info:
            execute_tool("bad_tool", {}, db)
        assert exc_info.value.code == "UNKNOWN_TOOL"
        assert exc_info.value.status_code == 400

    @patch(
        "cost_query_pro.services.agent_tools.compute_summary",
        return_value=_COST_SUMMARY,
    )
    @patch("cost_query_pro.services.agent_tools.run_search", return_value=[MagicMock()])
    def test_result_is_json_serializable_dict(self, mock_search, mock_summary):
        db = _make_db()
        result = execute_tool("keyword_search", {"keyword": "pipe"}, db)
        assert isinstance(result, dict)
        # All values must be basic Python types (model_dump output)
        for key, val in result.items():
            assert isinstance(val, (int, float, str, list, bool, type(None)))
