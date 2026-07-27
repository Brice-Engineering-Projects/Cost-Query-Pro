"""tests/unit_tests/test_intent_parser.py

Unit tests for the intent parsing service.
All LLM provider calls are mocked — no live API calls.
"""

from unittest.mock import MagicMock

import pytest

from cost_query_pro.core.errors import AppError
from cost_query_pro.schemas.agent import SearchParameters
from cost_query_pro.services.intent_parser import parse_intent
from cost_query_pro.services.llm_provider import CompletionResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_JSON = (
    '{"intent": "cost_search", "item": "24-inch ductile iron pipe",'
    ' "state": "FL", "year_start": 2021, "year_end": 2026}'
)

VALID_JSON_WITH_OPTIONALS = (
    '{"intent": "cost_search", "item": "steel pipe",'
    ' "state": "TX", "year_start": 2020, "year_end": 2025,'
    ' "unit": "LF", "price_min": 100.0, "price_max": 500.0}'
)


def _make_provider(return_value: str) -> MagicMock:
    provider = MagicMock()
    provider.complete.return_value = CompletionResult(
        text=return_value,
        provider="claude",
        model="claude-sonnet-4-6",
        input_tokens=120,
        output_tokens=40,
    )
    return provider


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseIntent:
    def test_parse_intent_valid_json(self):
        provider = _make_provider(VALID_JSON)
        result = parse_intent("Some question", provider)

        assert isinstance(result, SearchParameters)
        assert result.intent == "cost_search"
        assert result.item == "24-inch ductile iron pipe"
        assert result.state == "FL"
        assert result.year_start == 2021
        assert result.year_end == 2026

    def test_parse_intent_strips_code_fences(self):
        fenced = f"```json\n{VALID_JSON}\n```"
        provider = _make_provider(fenced)
        result = parse_intent("Some question", provider)

        assert result.item == "24-inch ductile iron pipe"
        assert result.state == "FL"

    def test_parse_intent_strips_plain_code_fences(self):
        fenced = f"```\n{VALID_JSON}\n```"
        provider = _make_provider(fenced)
        result = parse_intent("Some question", provider)

        assert result.state == "FL"

    def test_parse_intent_invalid_json_raises_app_error(self):
        provider = _make_provider("this is not json at all")
        with pytest.raises(AppError) as exc_info:
            parse_intent("Some question", provider)

        assert exc_info.value.code == "INTENT_PARSE_ERROR"
        assert exc_info.value.status_code == 400

    def test_parse_intent_missing_required_field_raises(self):
        # Missing 'item' field
        incomplete = '{"intent": "cost_search", "state": "FL", "year_start": 2021, "year_end": 2026}'
        provider = _make_provider(incomplete)
        with pytest.raises(AppError) as exc_info:
            parse_intent("Some question", provider)

        assert exc_info.value.code == "INTENT_PARSE_ERROR"

    def test_parse_intent_passes_system_prompt(self):
        provider = _make_provider(VALID_JSON)
        parse_intent("Some question", provider)

        call_kwargs = provider.complete.call_args.kwargs
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 0
        assert "cost_search" in call_kwargs["system"]

    def test_parse_intent_passes_request_id(self):
        provider = _make_provider(VALID_JSON)
        parse_intent("Some question", provider, request_id="req-abc-123")

        call_kwargs = provider.complete.call_args.kwargs
        assert call_kwargs.get("request_id") == "req-abc-123"

    def test_parse_intent_optional_fields_populated(self):
        provider = _make_provider(VALID_JSON_WITH_OPTIONALS)
        result = parse_intent("Some question", provider)

        assert result.unit == "LF"
        assert result.price_min == 100.0
        assert result.price_max == 500.0

    def test_parse_intent_optional_fields_absent(self):
        provider = _make_provider(VALID_JSON)
        result = parse_intent("Some question", provider)

        assert result.unit is None
        assert result.price_min is None
        assert result.price_max is None
