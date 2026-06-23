"""src/cost_query_pro/services/llm_provider.py

LLM provider abstraction layer.

Claude (claude-sonnet-4-6) is the primary provider. OpenAI (gpt-4o) is the
automatic fallback when Claude returns a non-retryable error. Neither SDK is
referenced outside this module.
"""

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import anthropic
import openai

from cost_query_pro.core.errors import AppError

if TYPE_CHECKING:
    from cost_query_pro.config.settings import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface every provider must implement."""

    name: str

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        request_id: str | None = None,
    ) -> str:
        """Send messages and return the assistant text reply."""
        ...


# ---------------------------------------------------------------------------
# Claude provider
# ---------------------------------------------------------------------------


class ClaudeProvider:
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        request_id: str | None = None,
    ) -> str:
        kwargs: dict = dict(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
        )
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        return next(b.text for b in response.content if b.type == "text")


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        request_id: str | None = None,
    ) -> str:
        full_messages: list[dict[str, str]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=full_messages,  # type: ignore[arg-type]
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Fallback provider (Claude → OpenAI)
# ---------------------------------------------------------------------------


class FallbackLLMProvider:
    """Calls the primary provider and falls back to the secondary on any error."""

    name = "fallback"

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        request_id: str | None = None,
    ) -> str:
        try:
            return self._primary.complete(
                messages,
                system=system,
                max_tokens=max_tokens,
                request_id=request_id,
            )
        except (anthropic.APIError, anthropic.APIConnectionError) as exc:
            logger.warning(
                "Provider '%s' error %s on request %s; falling back to '%s': %s",
                self._primary.name,
                type(exc).__name__,
                request_id,
                self._fallback.name,
                str(exc),
            )
            return self._fallback.complete(
                messages,
                system=system,
                max_tokens=max_tokens,
                request_id=request_id,
            )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_provider(settings: "Settings") -> LLMProvider:
    """
    Construct the configured LLM provider from settings.

    - Both keys present → FallbackLLMProvider(Claude → OpenAI)
    - Only ANTHROPIC_API_KEY set → ClaudeProvider (no fallback; warning logged)
    - ANTHROPIC_API_KEY missing when llm_provider == "claude" → AppError (request-time error)
    - llm_provider == "openai" and OPENAI_API_KEY missing → AppError
    """
    claude_provider: ClaudeProvider | None = None
    openai_provider: OpenAIProvider | None = None

    if settings.anthropic_api_key:
        claude_provider = ClaudeProvider(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
        )

    if settings.openai_api_key:
        openai_provider = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    if settings.llm_provider == "claude":
        if claude_provider is None:
            raise AppError(
                "LLM_KEY_MISSING",
                "ANTHROPIC_API_KEY is required but not configured.",
                500,
            )
        if openai_provider is None:
            logger.warning(
                "OPENAI_API_KEY not set — OpenAI fallback unavailable for Claude provider."
            )
            return claude_provider
        return FallbackLLMProvider(primary=claude_provider, fallback=openai_provider)

    if settings.llm_provider == "openai":
        if openai_provider is None:
            raise AppError(
                "LLM_KEY_MISSING",
                "OPENAI_API_KEY is required but not configured.",
                500,
            )
        return openai_provider

    raise AppError(
        "LLM_INVALID_PROVIDER",
        f"Unknown LLM_PROVIDER value: '{settings.llm_provider}'. Expected 'claude' or 'openai'.",
        500,
    )


def get_llm_provider() -> LLMProvider:
    """FastAPI Depends-compatible factory. Raises AppError if the configured key is absent."""
    from cost_query_pro.config.settings import settings

    return build_provider(settings)
