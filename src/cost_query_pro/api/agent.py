"""src/cost_query_pro/api/agent.py

POST /api/v1/agent/query — natural language cost search endpoint.

Orchestrates the five-step secure query pipeline and returns a structured
response. JWT authentication is required; the LLM never accesses the database
directly; only aggregate statistics are included in any LLM payload.
"""

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cost_query_pro.config.settings import settings
from cost_query_pro.core.errors import AppError
from cost_query_pro.core.security import get_current_user
from cost_query_pro.db.session import get_db
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.agent import (
    AgentQueryRequest,
    AgentQueryResponse,
    SearchScopeOut,
)
from cost_query_pro.services.analytics import compute_summary
from cost_query_pro.services.intent_parser import parse_intent
from cost_query_pro.services.item_search import run_search
from cost_query_pro.services.llm_provider import MeteredProvider, get_llm_provider
from cost_query_pro.services.response_generator import generate_response
from cost_query_pro.services.usage_recorder import record_usage

router = APIRouter()
logger = logging.getLogger(__name__)

_CLARIFYING_ANSWER = (
    "I wasn't able to identify a specific construction item or search criteria "
    "from your question. Could you rephrase it? For example: "
    '"What have Florida utilities paid for 8-inch PVC pipe in the last 3 years?"'
)


def _configured_model(provider_name: str) -> str:
    """Map provider name to the configured model identifier.

    Only a fallback for when no call has been made yet — a configured name says
    nothing about which provider actually served a request. Prefer
    :func:`_observed_model`.
    """
    if provider_name == "openai":
        return settings.openai_model
    return settings.claude_model  # "claude" and "fallback" both start on Claude


def _observed_model(provider: MeteredProvider) -> str:
    """The model that actually served this request.

    Reads the last recorded completion rather than the configured provider
    name, so a request that failed over from Claude to OpenAI reports the model
    that really answered it instead of always reporting Claude.
    """
    if provider.calls:
        return provider.calls[-1].model
    return _configured_model(provider.name)


def _observed_provider(provider: MeteredProvider) -> str:
    """The provider that actually served this request (see :func:`_observed_model`)."""
    if provider.calls:
        return provider.calls[-1].provider
    return provider.name


def _empty_scope() -> SearchScopeOut:
    return SearchScopeOut(item="", state="US", year_start=1900, year_end=2100)


@router.post("/agent/query", response_model=AgentQueryResponse)
def agent_query(
    body: AgentQueryRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
    provider: MeteredProvider = Depends(get_llm_provider),
) -> AgentQueryResponse:
    """Natural language cost query endpoint.

    Steps:
      1. Parse user question into SearchParameters (LLM call 1).
      2. Run search against the database.
      3. Compute aggregate statistics.
      4. Sanitize: only aggregate stats enter the LLM payload.
      5. Generate natural-language answer (LLM call 2).

    Graceful degradation:
      - Ambiguous question → 200 with a clarifying question (no error).
      - No matching records → 200 with a friendly explanation (no error).
    """
    request_id = body.request_id or str(uuid4())

    logger.info(
        "agent_query started (request_id=%s, user=%s)",
        request_id,
        current_user.username,
    )

    def _record() -> None:
        """Persist token usage for whatever calls this request made so far.

        Called on every exit path, including the two graceful-degradation
        returns — an ambiguous question or an empty result set still spends
        tokens, and unrecorded spend would undercount the monthly total.
        """
        record_usage(
            db,
            user_id=current_user.id,
            request_id=request_id,
            calls=provider.calls,
        )

    # ── Step 1: Parse intent ──────────────────────────────────────────────────
    try:
        params = parse_intent(body.question, provider, request_id=request_id)
    except AppError as exc:
        if exc.code == "INTENT_PARSE_ERROR":
            logger.info(
                "Intent parse failed — returning clarifying question (request_id=%s)",
                request_id,
            )
            _record()
            return AgentQueryResponse(
                answer=_CLARIFYING_ANSWER,
                record_count=0,
                search_scope=_empty_scope(),
                provider=_observed_provider(provider),
                model=_observed_model(provider),
                request_id=request_id,
            )
        _record()
        raise

    scope = SearchScopeOut(
        item=params.item,
        state=params.state,
        year_start=params.year_start,
        year_end=params.year_end,
        unit=params.unit,
        price_min=params.price_min,
        price_max=params.price_max,
    )

    # ── Steps 2–3: Search + analytics ────────────────────────────────────────
    try:
        items = run_search(params, db)
        summary = compute_summary(items)
    except AppError as exc:
        if exc.code == "NO_RESULTS":
            state_label = "any state" if params.state == "US" else params.state
            logger.info("No results found (request_id=%s)", request_id)
            _record()
            return AgentQueryResponse(
                answer=(
                    f"No records were found for '{params.item}' in {state_label} "
                    f"({params.year_start}–{params.year_end}). "
                    "Try broadening your search — a wider year range or a different "
                    "state may return results."
                ),
                record_count=0,
                search_scope=scope,
                provider=_observed_provider(provider),
                model=_observed_model(provider),
                request_id=request_id,
            )
        _record()
        raise

    # ── Steps 4–5: Sanitize + generate response ───────────────────────────────
    answer = generate_response(
        body.question, summary, params, provider, request_id=request_id
    )

    logger.info(
        "agent_query complete (request_id=%s, records=%d)",
        request_id,
        summary.record_count,
    )

    _record()
    return AgentQueryResponse(
        answer=answer,
        record_count=summary.record_count,
        search_scope=scope,
        provider=_observed_provider(provider),
        model=_observed_model(provider),
        request_id=request_id,
    )
