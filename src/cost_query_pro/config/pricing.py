"""src/cost_query_pro/config/pricing.py

Model pricing table used to estimate the cost of each LLM call.

Rates are USD per million tokens, as ``(input_rate, output_rate)``. These are
operator-maintained constants, not values reported by the provider APIs — the
SDKs return token counts, never prices. Verify them against the provider
pricing pages when adding a model or when a provider changes rates:

  - Anthropic: https://platform.claude.com/docs/en/pricing
  - OpenAI:    https://openai.com/api/pricing

Rates last reviewed: 2026-07-26.

Unknown models are deliberately *not* priced at zero. ``estimate_cost_usd``
returns ``None`` so the usage row records the token counts with a NULL cost,
which keeps "we do not know the price" distinguishable from "this call was
free" when summing a monthly spend total.
"""

import logging

logger = logging.getLogger(__name__)

# model identifier -> (USD per 1M input tokens, USD per 1M output tokens)
USD_PER_MTOK: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}

_TOKENS_PER_MILLION = 1_000_000

# Models already warned about, so an unpriced model logs once per process
# rather than once per request.
_warned_models: set[str] = set()


def estimate_cost_usd(
    model: str, input_tokens: int, output_tokens: int
) -> float | None:
    """Estimate the USD cost of a single completion.

    Returns ``None`` for a model absent from :data:`USD_PER_MTOK`, logging a
    warning the first time that model is seen. Callers should persist the
    ``None`` rather than coercing it to ``0.0``.
    """
    rates = USD_PER_MTOK.get(model)
    if rates is None:
        if model not in _warned_models:
            _warned_models.add(model)
            logger.warning(
                "No pricing entry for model '%s' — usage will be recorded with a "
                "NULL cost and excluded from spend totals. Add it to "
                "cost_query_pro.config.pricing.USD_PER_MTOK.",
                model,
            )
        return None

    input_rate, output_rate = rates
    return (
        input_tokens * input_rate + output_tokens * output_rate
    ) / _TOKENS_PER_MILLION
