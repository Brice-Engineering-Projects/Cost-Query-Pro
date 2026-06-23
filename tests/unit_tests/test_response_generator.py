"""tests/unit_tests/test_response_generator.py

Unit tests for the response generator service (Steps 4 & 5).
All LLM provider calls are mocked — no live API calls.
Includes a security boundary test verifying that raw project data
is never included in outbound LLM payloads.
"""

from unittest.mock import MagicMock

from cost_query_pro.schemas.agent import CostSummary, SearchParameters
from cost_query_pro.services.response_generator import (
    _build_user_message,
    generate_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

QUESTION = "What have Florida utilities been paying for 24-inch ductile iron pipe?"


def _make_provider(return_value: str = "Based on 147 records...") -> MagicMock:
    p = MagicMock()
    p.complete.return_value = return_value
    return p


def _make_summary(**overrides) -> CostSummary:
    defaults = dict(
        record_count=147,
        median_price=212.0,
        average_price=219.0,
        minimum_price=180.0,
        maximum_price=287.0,
    )
    defaults.update(overrides)
    return CostSummary(**defaults)


def _make_params(**overrides) -> SearchParameters:
    defaults = dict(
        intent="cost_search",
        item="24-inch ductile iron pipe",
        state="FL",
        year_start=2021,
        year_end=2026,
    )
    defaults.update(overrides)
    return SearchParameters(**defaults)


# ---------------------------------------------------------------------------
# Tests — generate_response
# ---------------------------------------------------------------------------


class TestGenerateResponse:
    def test_returns_provider_response(self):
        provider = _make_provider("Some LLM answer")
        result = generate_response(QUESTION, _make_summary(), _make_params(), provider)
        assert result == "Some LLM answer"

    def test_passes_system_prompt(self):
        provider = _make_provider()
        generate_response(QUESTION, _make_summary(), _make_params(), provider)

        call_kwargs = provider.complete.call_args.kwargs
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 0

    def test_passes_request_id(self):
        provider = _make_provider()
        generate_response(
            QUESTION, _make_summary(), _make_params(), provider, request_id="req-xyz"
        )

        call_kwargs = provider.complete.call_args.kwargs
        assert call_kwargs.get("request_id") == "req-xyz"

    def test_user_message_contains_question(self):
        provider = _make_provider()
        generate_response(QUESTION, _make_summary(), _make_params(), provider)

        sent_message = provider.complete.call_args.args[0][0]["content"]
        assert QUESTION in sent_message

    def test_user_message_contains_summary_stats(self):
        summary = _make_summary(
            record_count=50,
            median_price=150.0,
            average_price=160.0,
            minimum_price=100.0,
            maximum_price=220.0,
        )
        provider = _make_provider()
        generate_response(QUESTION, summary, _make_params(), provider)

        sent_message = provider.complete.call_args.args[0][0]["content"]
        assert "50" in sent_message  # record_count
        assert "150.00" in sent_message  # median
        assert "160.00" in sent_message  # average
        assert "100.00" in sent_message  # minimum
        assert "220.00" in sent_message  # maximum

    def test_user_message_contains_search_scope(self):
        params = _make_params(
            item="steel pipe", state="TX", year_start=2019, year_end=2024
        )
        provider = _make_provider()
        generate_response(QUESTION, _make_summary(), params, provider)

        sent_message = provider.complete.call_args.args[0][0]["content"]
        assert "steel pipe" in sent_message
        assert "TX" in sent_message
        assert "2019" in sent_message
        assert "2024" in sent_message

    def test_us_state_rendered_as_all_states(self):
        params = _make_params(state="US")
        provider = _make_provider()
        generate_response(QUESTION, _make_summary(), params, provider)

        sent_message = provider.complete.call_args.args[0][0]["content"]
        assert "all states" in sent_message

    def test_security_boundary_no_raw_project_data(self):
        """Security boundary: verify raw project-identifying data is never in the LLM payload.

        The outbound message must contain only CostSummary aggregate fields,
        search scope metadata, and the user's original question. It must NOT
        contain column names or field names that correspond to raw project records.
        """
        forbidden_terms = [
            "project_name",
            "project_number",
            "contractor",
            "bid_tabulation",
            "source_file",
            "raw_record",
            "upload_id",
            "internal_note",
        ]
        provider = _make_provider()
        generate_response(QUESTION, _make_summary(), _make_params(), provider)

        sent_message = provider.complete.call_args.args[0][0]["content"].lower()
        for term in forbidden_terms:
            assert (
                term not in sent_message
            ), f"Security boundary violated: '{term}' found in LLM payload"


# ---------------------------------------------------------------------------
# Tests — _build_user_message (unit-test the sanitizer directly)
# ---------------------------------------------------------------------------


class TestBuildUserMessage:
    def test_all_five_stats_present(self):
        summary = _make_summary(
            record_count=10,
            median_price=100.0,
            average_price=110.0,
            minimum_price=80.0,
            maximum_price=140.0,
        )
        msg = _build_user_message("question", summary, _make_params())
        assert "10" in msg
        assert "100.00" in msg
        assert "110.00" in msg
        assert "80.00" in msg
        assert "140.00" in msg

    def test_us_placeholder_renders_as_all_states(self):
        msg = _build_user_message("question", _make_summary(), _make_params(state="US"))
        assert "all states" in msg
        assert "US" not in msg

    def test_explicit_state_renders_as_state_code(self):
        msg = _build_user_message("question", _make_summary(), _make_params(state="CA"))
        assert "CA" in msg
        assert "all states" not in msg
