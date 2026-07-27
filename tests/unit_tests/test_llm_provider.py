"""tests/unit_tests/test_llm_provider.py

Unit tests for the LLM provider abstraction layer.
All Anthropic and OpenAI clients are mocked — no live API calls.
"""

from unittest.mock import MagicMock, patch

import anthropic
import httpx
import pytest

from cost_query_pro.core.errors import AppError
from cost_query_pro.services.llm_provider import (
    ClaudeProvider,
    CompletionResult,
    FallbackLLMProvider,
    OpenAIProvider,
    build_provider,
)


def _sentinel(text: str) -> CompletionResult:
    """A stand-in completion for provider-routing tests.

    A real CompletionResult rather than a bare string, so the assertion
    exercises the declared return contract of complete().
    """
    return CompletionResult(
        text=text,
        provider="stub",
        model="stub-model",
        input_tokens=0,
        output_tokens=0,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_anthropic_response(
    text: str,
    *,
    model: str = "claude-sonnet-4-6",
    input_tokens: int = 100,
    output_tokens: int = 25,
) -> MagicMock:
    """Build a mock anthropic Messages response."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    msg.model = model
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


def _make_openai_response(
    text: str,
    *,
    model: str = "gpt-4o",
    prompt_tokens: int = 100,
    completion_tokens: int = 25,
) -> MagicMock:
    """Build a mock OpenAI ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    resp.model = model
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    return resp


def _make_settings(
    anthropic_key: str | None = "sk-ant-test",
    openai_key: str | None = "sk-oai-test",
    provider: str = "claude",
    claude_model: str = "claude-sonnet-4-6",
    openai_model: str = "gpt-4o",
) -> MagicMock:
    s = MagicMock()
    s.anthropic_api_key = anthropic_key
    s.openai_api_key = openai_key
    s.llm_provider = provider
    s.claude_model = claude_model
    s.openai_model = openai_model
    return s


def _make_auth_error() -> anthropic.AuthenticationError:
    return anthropic.AuthenticationError(
        message="invalid key",
        response=httpx.Response(
            401, request=httpx.Request("POST", "https://api.anthropic.com")
        ),
        body=None,
    )


def _make_api_connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(
        message="connection refused",
        request=httpx.Request("POST", "https://api.anthropic.com"),
    )


# ---------------------------------------------------------------------------
# ClaudeProvider
# ---------------------------------------------------------------------------


class TestClaudeProvider:
    def test_complete_returns_text(self):
        provider = ClaudeProvider(api_key="sk-ant-test")
        mock_resp = _make_anthropic_response("Hello from Claude")

        with patch.object(provider._client.messages, "create", return_value=mock_resp):
            result = provider.complete([{"role": "user", "content": "Hi"}])

        assert result.text == "Hello from Claude"
        assert result.provider == "claude"
        assert result.model == "claude-sonnet-4-6"
        assert result.input_tokens == 100
        assert result.output_tokens == 25

    def test_complete_passes_system_prompt(self):
        provider = ClaudeProvider(api_key="sk-ant-test")
        mock_resp = _make_anthropic_response("ok")

        with patch.object(
            provider._client.messages, "create", return_value=mock_resp
        ) as mock_create:
            provider.complete(
                [{"role": "user", "content": "Hi"}],
                system="You are helpful.",
            )

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("system") == "You are helpful."

    def test_complete_omits_system_when_none(self):
        provider = ClaudeProvider(api_key="sk-ant-test")
        mock_resp = _make_anthropic_response("ok")

        with patch.object(
            provider._client.messages, "create", return_value=mock_resp
        ) as mock_create:
            provider.complete([{"role": "user", "content": "Hi"}], system=None)

        call_kwargs = mock_create.call_args.kwargs
        assert "system" not in call_kwargs


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    def test_complete_returns_text(self):
        provider = OpenAIProvider(api_key="sk-oai-test")
        mock_resp = _make_openai_response("Hello from OpenAI")

        with patch.object(
            provider._client.chat.completions, "create", return_value=mock_resp
        ):
            result = provider.complete([{"role": "user", "content": "Hi"}])

        assert result.text == "Hello from OpenAI"
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
        assert result.input_tokens == 100
        assert result.output_tokens == 25

    def test_complete_prepends_system_message(self):
        provider = OpenAIProvider(api_key="sk-oai-test")
        mock_resp = _make_openai_response("ok")

        with patch.object(
            provider._client.chat.completions, "create", return_value=mock_resp
        ) as mock_create:
            provider.complete(
                [{"role": "user", "content": "Hi"}],
                system="Be concise.",
            )

        sent_messages = mock_create.call_args.kwargs["messages"]
        assert sent_messages[0] == {"role": "system", "content": "Be concise."}
        assert sent_messages[1] == {"role": "user", "content": "Hi"}

    def test_complete_no_system_message_when_none(self):
        provider = OpenAIProvider(api_key="sk-oai-test")
        mock_resp = _make_openai_response("ok")

        with patch.object(
            provider._client.chat.completions, "create", return_value=mock_resp
        ) as mock_create:
            provider.complete([{"role": "user", "content": "Hi"}], system=None)

        sent_messages = mock_create.call_args.kwargs["messages"]
        assert len(sent_messages) == 1
        assert sent_messages[0]["role"] == "user"


# ---------------------------------------------------------------------------
# FallbackLLMProvider
# ---------------------------------------------------------------------------


class TestFallbackLLMProvider:
    def test_primary_success_returns_primary_result(self):
        primary = MagicMock(name="claude")
        primary.name = "claude"
        primary.complete.return_value = _sentinel("from primary")
        fallback = MagicMock(name="openai")
        fallback.name = "openai"

        provider = FallbackLLMProvider(primary=primary, fallback=fallback)
        result = provider.complete([{"role": "user", "content": "hi"}])

        assert result == _sentinel("from primary")
        fallback.complete.assert_not_called()

    def test_fallback_on_auth_error(self):
        primary = MagicMock(name="claude")
        primary.name = "claude"
        primary.complete.side_effect = _make_auth_error()
        fallback = MagicMock(name="openai")
        fallback.name = "openai"
        fallback.complete.return_value = _sentinel("from fallback")

        provider = FallbackLLMProvider(primary=primary, fallback=fallback)
        with patch("cost_query_pro.services.llm_provider.logger") as mock_log:
            result = provider.complete(
                [{"role": "user", "content": "hi"}], request_id="req-123"
            )

        assert result == _sentinel("from fallback")
        fallback.complete.assert_called_once()
        mock_log.warning.assert_called_once()
        warning_args = str(mock_log.warning.call_args)
        assert "req-123" in warning_args
        assert "AuthenticationError" in warning_args

    def test_fallback_on_connection_error(self):
        primary = MagicMock(name="claude")
        primary.name = "claude"
        primary.complete.side_effect = _make_api_connection_error()
        fallback = MagicMock(name="openai")
        fallback.name = "openai"
        fallback.complete.return_value = _sentinel("from fallback")

        provider = FallbackLLMProvider(primary=primary, fallback=fallback)
        with patch("cost_query_pro.services.llm_provider.logger") as mock_log:
            result = provider.complete(
                [{"role": "user", "content": "hi"}], request_id="req-456"
            )

        assert result == _sentinel("from fallback")
        mock_log.warning.assert_called_once()
        assert "APIConnectionError" in str(mock_log.warning.call_args)


# ---------------------------------------------------------------------------
# build_provider
# ---------------------------------------------------------------------------


class TestBuildProvider:
    def test_both_keys_returns_fallback_provider(self):
        settings = _make_settings()
        provider = build_provider(settings)
        assert isinstance(provider, FallbackLLMProvider)

    def test_claude_key_only_returns_claude_provider(self):
        settings = _make_settings(openai_key=None)
        with patch("cost_query_pro.services.llm_provider.logger") as mock_log:
            provider = build_provider(settings)
        assert isinstance(provider, ClaudeProvider)
        mock_log.warning.assert_called_once()
        assert "OPENAI_API_KEY" in str(mock_log.warning.call_args)

    def test_missing_anthropic_key_raises_app_error(self):
        settings = _make_settings(anthropic_key=None)
        with pytest.raises(AppError) as exc_info:
            build_provider(settings)
        assert exc_info.value.code == "LLM_KEY_MISSING"
        assert exc_info.value.status_code == 500

    def test_openai_provider_selection(self):
        settings = _make_settings(anthropic_key=None, provider="openai")
        provider = build_provider(settings)
        assert isinstance(provider, OpenAIProvider)

    def test_openai_provider_missing_key_raises(self):
        settings = _make_settings(
            anthropic_key=None, openai_key=None, provider="openai"
        )
        with pytest.raises(AppError) as exc_info:
            build_provider(settings)
        assert exc_info.value.code == "LLM_KEY_MISSING"

    def test_invalid_provider_raises_app_error(self):
        settings = _make_settings(provider="invalid")
        with pytest.raises(AppError) as exc_info:
            build_provider(settings)
        assert exc_info.value.code == "LLM_INVALID_PROVIDER"
