"""src/cost_query_pro/services/response_generator.py

Steps 4 & 5 of the Secure Query Pipeline:
  Step 4 — Data sanitization: only CostSummary aggregate fields are included
             in the LLM payload; no raw records or project-identifying data.
  Step 5 — Response generation: LLM receives the sanitized summary and the
             user's original question, and returns a natural-language answer.
"""

import logging
from typing import Optional

from cost_query_pro.schemas.agent import CostSummary, SearchParameters
from cost_query_pro.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a construction cost analyst. Your role is to interpret aggregate price \
statistics and explain them clearly to infrastructure professionals.

You will receive:
1. The user's original question.
2. Aggregate statistics from a database query (record count, median, average, min, max).

You must:
- Write a concise, professional answer using only the statistics provided.
- State the number of records found.
- Quote the median and average prices.
- Note the price range (min to max).
- Mention the search filters (item, state, year range) so the user can verify scope.

You must NOT:
- Invent data or extrapolate beyond what the statistics show.
- Reference individual project names, project numbers, contractors, or bid records.
- Generate SQL, access databases, or claim to have done so."""


def _build_user_message(
    question: str,
    summary: CostSummary,
    params: SearchParameters,
) -> str:
    """Build the sanitized user-turn message for the LLM.

    Contains only CostSummary aggregate fields and the search scope.
    Raw records, project names, numbers, and contractor data are never included.
    """
    state_label = "all states" if params.state == "US" else params.state
    return (
        f"User question: {question}\n\n"
        f"Search scope:\n"
        f"  Item: {params.item}\n"
        f"  State: {state_label}\n"
        f"  Years: {params.year_start}\u2013{params.year_end}\n\n"
        f"Aggregate statistics ({summary.record_count} records):\n"
        f"  Median unit price:  ${summary.median_price:,.2f}\n"
        f"  Average unit price: ${summary.average_price:,.2f}\n"
        f"  Minimum unit price: ${summary.minimum_price:,.2f}\n"
        f"  Maximum unit price: ${summary.maximum_price:,.2f}"
    )


def generate_response(
    question: str,
    summary: CostSummary,
    params: SearchParameters,
    provider: LLMProvider,
    *,
    request_id: Optional[str] = None,
) -> str:
    """Generate a natural-language answer from sanitized aggregate statistics.

    This is the second LLM call in the secure query pipeline. The LLM receives
    only the CostSummary and the user's question — no raw records or project data.

    Args:
        question: The user's original natural-language question.
        summary: Aggregate statistics from the analytics layer (Step 3).
        params: SearchParameters used to scope the DB query (for context in the answer).
        provider: An LLMProvider instance.
        request_id: Optional ID for log correlation.

    Returns:
        Natural-language response string.
    """
    user_message = _build_user_message(question, summary, params)
    messages = [{"role": "user", "content": user_message}]

    response = provider.complete(
        messages,
        system=_SYSTEM_PROMPT,
        max_tokens=1024,
        request_id=request_id,
    )

    logger.info(
        "generate_response completed (request_id=%s, records=%d)",
        request_id,
        summary.record_count,
    )
    return response
