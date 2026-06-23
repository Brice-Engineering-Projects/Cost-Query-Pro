"""src/cost_query_pro/services/intent_parser.py

Step 1 of the Secure Query Pipeline: parse a user question into validated
SearchParameters via the LLM. No database access occurs in this module.
"""

import logging
import re
from typing import Optional

from cost_query_pro.core.errors import AppError
from cost_query_pro.schemas.agent import SearchParameters
from cost_query_pro.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

_CURRENT_YEAR = 2026

_SYSTEM_PROMPT = """\
You are a search parameter extractor for a construction cost database.

Extract search criteria from the user's question and return ONLY a JSON object with these fields:

Required fields:
- "intent": always the string "cost_search"
- "item": a short description of the construction item or material being searched for
- "state": the two-letter US state code (e.g. "FL", "TX", "CA")
- "year_start": the start year as an integer
- "year_end": the end year as an integer

Optional fields (include only if explicitly mentioned):
- "unit": unit of measure (e.g. "LF", "EA", "CY")
- "price_min": minimum unit price as a number
- "price_max": maximum unit price as a number

Rules:
- Return ONLY the JSON object. No explanation, no markdown, no code fences.
- If no year range is given, use year_start = current_year - 5 and year_end = current_year.
- If no state is mentioned, use "US" as a placeholder (the backend will handle it).
- Do NOT generate SQL or access any database.
- Do NOT invent data — extract only what the user stated.

Current year: {current_year}"""


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if the LLM wrapped its JSON response."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1)
    return text


def parse_intent(
    question: str,
    provider: LLMProvider,
    *,
    request_id: Optional[str] = None,
) -> SearchParameters:
    """Call the LLM to extract SearchParameters from a natural language question.

    The LLM receives only the user's question — no database data is exposed.

    Args:
        question: The user's natural language question.
        provider: An LLMProvider instance (ClaudeProvider, FallbackLLMProvider, etc.).
        request_id: Optional ID for log correlation.

    Returns:
        A validated SearchParameters instance.

    Raises:
        AppError: code='INTENT_PARSE_ERROR', status=400 if the LLM response
                  cannot be parsed as valid SearchParameters.
    """
    system = _SYSTEM_PROMPT.format(current_year=_CURRENT_YEAR)
    messages = [{"role": "user", "content": question}]

    raw = provider.complete(
        messages, system=system, max_tokens=512, request_id=request_id
    )
    logger.debug("Intent parser raw LLM response (request_id=%s): %s", request_id, raw)

    cleaned = _strip_code_fences(raw)

    try:
        params = SearchParameters.model_validate_json(cleaned)
    except Exception as exc:
        logger.warning(
            "Intent parser failed to parse LLM output (request_id=%s): %s | raw=%r",
            request_id,
            exc,
            raw,
        )
        raise AppError(
            "INTENT_PARSE_ERROR",
            "Could not extract search parameters from your question. Please rephrase and try again.",
            400,
        ) from exc

    return params
