# LLM Provider — Selection and Fallback

Cost Query Pro routes all AI calls through a single abstraction layer (`services/llm_provider.py`). No other module imports the Anthropic or OpenAI SDKs directly.

---

## Default Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_PROVIDER` | `claude` | Active primary provider (`claude` or `openai`) |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Anthropic model ID |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model ID |
| `ANTHROPIC_API_KEY` | *(none)* | Required when `LLM_PROVIDER=claude` |
| `OPENAI_API_KEY` | *(none)* | Required for OpenAI fallback |

All values are read from the environment (or `.env` file). They map directly to fields on the Pydantic `Settings` class.

---

## Provider Selection

```
LLM_PROVIDER=claude   →  ClaudeProvider (primary)
                          + FallbackLLMProvider wrapping OpenAI (if OPENAI_API_KEY is set)

LLM_PROVIDER=openai   →  OpenAIProvider only (no fallback)
```

---

## Fallback Behavior

When `LLM_PROVIDER=claude` and `OPENAI_API_KEY` is also set, the active provider is `FallbackLLMProvider`. It:

1. Calls Claude first.
2. If Claude raises any `anthropic.APIError` or `anthropic.APIConnectionError` (including auth errors, model-not-found, rate limit exhaustion after SDK retries, and network failures), it **logs a WARNING** and calls OpenAI instead.
3. Returns the OpenAI response transparently.

If `OPENAI_API_KEY` is absent, Claude is used without a fallback and a warning is logged at startup.

### Fallback log format

```
WARNING cost_query_pro.services.llm_provider - Provider 'claude' error AuthenticationError on request <request_id>; falling back to 'openai': <detail>
```

The `request_id` field is set by the caller (agent endpoint) to allow tracing a specific query through logs.

---

## Startup Warnings

The server starts regardless of whether API keys are present. Missing keys are logged as warnings in the startup lifespan block:

| Condition | Warning message |
|-----------|-----------------|
| `LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY` unset | `ANTHROPIC_API_KEY is not set. Claude provider will error at request time.` |
| `OPENAI_API_KEY` unset | `OPENAI_API_KEY is not set. OpenAI fallback provider is unavailable.` |

When the agent endpoint is called and the configured primary key is absent, it returns HTTP 500 with code `LLM_KEY_MISSING`.

---

## Error Codes

| Code | HTTP | Cause |
|------|------|-------|
| `LLM_KEY_MISSING` | 500 | The configured primary provider has no API key |
| `LLM_INVALID_PROVIDER` | 500 | `LLM_PROVIDER` is set to an unknown value |

---

## FastAPI Dependency

```python
from fastapi import Depends
from cost_query_pro.services.llm_provider import get_llm_provider, LLMProvider

@router.post("/query")
def agent_query(provider: LLMProvider = Depends(get_llm_provider)):
    result = provider.complete(
        messages=[{"role": "user", "content": question}],
        system="You are a cost estimation assistant.",
        request_id=request_id,
    )
```

`get_llm_provider()` calls `build_provider(settings)` on each request. It raises `AppError("LLM_KEY_MISSING", ...)` if the configured provider has no key, which is handled by the global `AppError` handler and returned as a structured 500 JSON response.

---

## Provider Interface

All providers implement the same `LLMProvider` protocol:

```python
class LLMProvider(Protocol):
    name: str

    def complete(
        self,
        messages: list[dict[str, str]],  # [{"role": "user"|"assistant", "content": "..."}]
        *,
        system: str | None = None,       # Optional system prompt
        max_tokens: int = 4096,
        request_id: str | None = None,   # For log correlation
    ) -> str: ...
```
