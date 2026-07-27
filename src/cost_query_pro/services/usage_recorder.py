"""src/cost_query_pro/services/usage_recorder.py

Persists per-completion LLM token usage.

Follows the ingestion-service convention: the caller passes the Session, this
module owns the commit for its own unit of work.
"""

import logging

from sqlalchemy.orm import Session

from cost_query_pro.config.pricing import estimate_cost_usd
from cost_query_pro.models.llm_usage import LlmUsage
from cost_query_pro.services.llm_provider import CompletionResult

logger = logging.getLogger(__name__)

# Pipeline stage labels, in call order. Recorded per row so cost can be
# attributed to intent parsing vs. response generation.
STAGES = ("intent_parse", "generate_response")


def record_usage(
    db: Session,
    *,
    user_id: int,
    request_id: str,
    calls: list[CompletionResult],
) -> list[LlmUsage]:
    """Write one ``llm_usage`` row per completion and commit.

    ``calls`` is expected to be ``MeteredProvider.calls`` — in pipeline order,
    so it can be zipped against :data:`STAGES`. Extra calls beyond the known
    stages (a future tool-use loop makes an unbounded number) are labelled
    positionally rather than dropped.

    Never raises: usage accounting must not turn a successful answer into a
    failed request. A write failure is logged and rolled back.
    """
    if not calls:
        return []

    rows: list[LlmUsage] = []
    for index, call in enumerate(calls):
        stage = STAGES[index] if index < len(STAGES) else f"call_{index}"
        rows.append(
            LlmUsage(
                user_id=user_id,
                request_id=request_id,
                stage=stage,
                provider=call.provider,
                model=call.model,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                cost_usd=estimate_cost_usd(
                    call.model, call.input_tokens, call.output_tokens
                ),
            )
        )

    try:
        db.add_all(rows)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to record LLM usage (request_id=%s, calls=%d)",
            request_id,
            len(calls),
        )
        return []

    logger.info(
        "Recorded LLM usage (request_id=%s, calls=%d, input_tokens=%d, "
        "output_tokens=%d)",
        request_id,
        len(rows),
        sum(r.input_tokens for r in rows),
        sum(r.output_tokens for r in rows),
    )
    return rows
