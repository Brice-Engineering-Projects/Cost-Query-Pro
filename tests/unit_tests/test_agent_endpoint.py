"""tests/unit_tests/test_agent_endpoint.py

Unit tests for POST /api/v1/agent/query.

All pipeline service functions are patched; no live LLM calls or DB queries
are made. Dependencies (get_db, get_current_user, get_llm_provider) are
overridden via app.dependency_overrides.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cost_query_pro.core.errors import AppError
from cost_query_pro.core.security import get_current_user
from cost_query_pro.db.session import get_db
from cost_query_pro.main import app
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.agent import CostSummary, SearchParameters
from cost_query_pro.services.llm_provider import (
    CompletionResult,
    LLMProvider,
    MeteredProvider,
    get_llm_provider,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QUESTION = "What have Florida utilities paid for 8-inch PVC pipe?"

_PARAMS = SearchParameters(
    intent="cost_search",
    item="8-inch PVC pipe",
    state="FL",
    year_start=2021,
    year_end=2026,
    unit=None,
    price_min=None,
    price_max=None,
)

_SUMMARY = CostSummary(
    record_count=47,
    median_price=35.0,
    average_price=37.5,
    minimum_price=20.0,
    maximum_price=65.0,
)


def _make_mock_user() -> MagicMock:
    user = MagicMock(spec=DBUser)
    user.id = 1
    user.username = "testuser"
    user.is_admin = False
    return user


def _make_mock_provider(name: str = "claude") -> MeteredProvider:
    """A real MeteredProvider around a mocked inner provider.

    The endpoint reads ``provider.calls`` to attribute token usage, so the
    wrapper must be genuine — a ``MagicMock(spec=LLMProvider)`` has no ``calls``
    attribute and would raise on access.
    """
    inner = MagicMock(spec=LLMProvider)
    inner.name = name
    inner.complete.return_value = CompletionResult(
        text="Based on 47 records, the median price is $35.00/LF.",
        provider=name,
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=25,
    )
    return MeteredProvider(inner=inner)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_user():
    return _make_mock_user()


@pytest.fixture
def mock_provider():
    return _make_mock_provider()


@pytest.fixture
def agent_client(mock_user, mock_provider):
    """TestClient with all three agent endpoint dependencies overridden."""
    overrides = {
        get_db: lambda: MagicMock(),
        get_current_user: lambda: mock_user,
        get_llm_provider: lambda: mock_provider,
    }
    app.dependency_overrides.update(overrides)
    with TestClient(app) as c:
        yield c
    for key in overrides:
        app.dependency_overrides.pop(key, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch(
    "cost_query_pro.api.agent.generate_response",
    return_value="Median price is $35.00/LF.",
)
@patch("cost_query_pro.api.agent.compute_summary", return_value=_SUMMARY)
@patch("cost_query_pro.api.agent.run_search", return_value=[MagicMock()])
@patch("cost_query_pro.api.agent.parse_intent", return_value=_PARAMS)
class TestAgentQueryHappyPath:
    def test_query_returns_200_with_answer(
        self, mock_parse, mock_search, mock_summary, mock_generate, agent_client
    ):
        resp = agent_client.post("/api/v1/agent/query", json={"question": _QUESTION})
        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body
        assert "record_count" in body
        assert "search_scope" in body
        assert "provider" in body
        assert "model" in body
        assert "request_id" in body

    def test_search_scope_reflects_parsed_params(
        self, mock_parse, mock_search, mock_summary, mock_generate, agent_client
    ):
        resp = agent_client.post("/api/v1/agent/query", json={"question": _QUESTION})
        scope = resp.json()["search_scope"]
        assert scope["item"] == _PARAMS.item
        assert scope["state"] == _PARAMS.state
        assert scope["year_start"] == _PARAMS.year_start
        assert scope["year_end"] == _PARAMS.year_end

    def test_provider_name_in_response(
        self,
        mock_parse,
        mock_search,
        mock_summary,
        mock_generate,
        agent_client,
        mock_provider,
    ):
        resp = agent_client.post("/api/v1/agent/query", json={"question": _QUESTION})
        assert resp.json()["provider"] == mock_provider.name

    def test_custom_request_id_propagated(
        self, mock_parse, mock_search, mock_summary, mock_generate, agent_client
    ):
        resp = agent_client.post(
            "/api/v1/agent/query",
            json={"question": _QUESTION, "request_id": "test-req-123"},
        )
        assert resp.json()["request_id"] == "test-req-123"

    def test_auto_generates_request_id_when_absent(
        self, mock_parse, mock_search, mock_summary, mock_generate, agent_client
    ):
        resp = agent_client.post("/api/v1/agent/query", json={"question": _QUESTION})
        request_id = resp.json()["request_id"]
        assert isinstance(request_id, str)
        assert len(request_id) > 0


class TestAgentQueryAuth:
    def test_query_requires_jwt_auth(self):
        """No Authorization header → OAuth2PasswordBearer raises 401 before handler runs."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        try:
            with TestClient(app) as c:
                resp = c.post("/api/v1/agent/query", json={"question": _QUESTION})
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestAgentQueryGracefulDegradation:
    @patch("cost_query_pro.api.agent.parse_intent")
    def test_intent_parse_error_returns_clarifying_message(
        self, mock_parse, agent_client
    ):
        mock_parse.side_effect = AppError("INTENT_PARSE_ERROR", "Cannot parse.", 400)

        resp = agent_client.post("/api/v1/agent/query", json={"question": "huh???"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["record_count"] == 0
        assert "rephrase" in body["answer"].lower()

    @patch("cost_query_pro.api.agent.generate_response")
    @patch("cost_query_pro.api.agent.compute_summary")
    @patch("cost_query_pro.api.agent.run_search", return_value=[])
    @patch("cost_query_pro.api.agent.parse_intent", return_value=_PARAMS)
    def test_no_results_returns_friendly_message(
        self,
        mock_parse,
        mock_search,
        mock_summary,
        mock_generate,
        agent_client,
    ):
        mock_summary.side_effect = AppError("NO_RESULTS", "No matching records.", 404)

        resp = agent_client.post("/api/v1/agent/query", json={"question": _QUESTION})
        assert resp.status_code == 200
        body = resp.json()
        assert body["record_count"] == 0
        assert "No records" in body["answer"]
        mock_generate.assert_not_called()


# ---------------------------------------------------------------------------
# Provider / model attribution
# ---------------------------------------------------------------------------


class TestProviderAttribution:
    """The response must name the provider that actually served the request.

    Previously ``_resolve_model`` mapped the *configured* provider name, so a
    FallbackLLMProvider request answered by OpenAI still reported Claude.
    """

    @pytest.fixture
    def failover_client(self, mock_user):
        """A provider named 'fallback' whose completions were served by OpenAI."""
        inner = MagicMock(spec=LLMProvider)
        inner.name = "fallback"
        inner.complete.return_value = CompletionResult(
            text="Median price is $35.00/LF.",
            provider="openai",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=25,
        )
        provider = MeteredProvider(inner=inner)

        overrides = {
            get_db: lambda: MagicMock(),
            get_current_user: lambda: mock_user,
            get_llm_provider: lambda: provider,
        }
        app.dependency_overrides.update(overrides)
        with TestClient(app) as c:
            yield c
        for key in overrides:
            app.dependency_overrides.pop(key, None)

    @patch("cost_query_pro.api.agent.compute_summary", return_value=_SUMMARY)
    @patch("cost_query_pro.api.agent.run_search", return_value=[MagicMock()])
    @patch("cost_query_pro.api.agent.parse_intent", return_value=_PARAMS)
    def test_reports_the_model_that_actually_served(
        self, mock_parse, mock_search, mock_summary, failover_client
    ):
        # generate_response is left unpatched so the real call runs through the
        # metered provider and records a completion attributed to OpenAI.
        resp = failover_client.post("/api/v1/agent/query", json={"question": _QUESTION})
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "openai"
        assert body["model"] == "gpt-4o"

    @patch(
        "cost_query_pro.api.agent.generate_response",
        return_value="Median price is $35.00/LF.",
    )
    @patch("cost_query_pro.api.agent.compute_summary", return_value=_SUMMARY)
    @patch("cost_query_pro.api.agent.run_search", return_value=[MagicMock()])
    @patch("cost_query_pro.api.agent.parse_intent", return_value=_PARAMS)
    def test_falls_back_to_configured_model_when_no_call_was_made(
        self, mock_parse, mock_search, mock_summary, mock_generate, agent_client
    ):
        """With both LLM steps patched out, no completion is recorded."""
        resp = agent_client.post("/api/v1/agent/query", json={"question": _QUESTION})
        assert resp.status_code == 200
        assert resp.json()["provider"] == "claude"
