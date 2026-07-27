"""
src/cost_query_pro/models/llm_usage.py

LLM Usage Model:
----------------
One row per LLM completion, not per HTTP request — a single agent query makes
two calls (intent parsing and response generation), and a fallback failover can
split those across two providers. Recording per call keeps cost attribution
correct in both cases.

This table is the shared substrate for the Phase 2 cost-control work:
  - token log      → the rows themselves
  - rate limiting  → COUNT over ``created_at`` within a window
  - spend cap      → SUM(``cost_usd``) for the calendar month

``cost_usd`` is nullable on purpose: a model with no entry in
``config.pricing.USD_PER_MTOK`` records its token counts with a NULL cost, so
"unpriced" stays distinguishable from "free" when spend is summed.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base

if TYPE_CHECKING:
    from cost_query_pro.models.user import User


class LlmUsage(Base):
    __tablename__ = "llm_usage"

    __table_args__ = (
        # Serves both the per-user rate-limit COUNT and the per-user spend SUM.
        Index("ix_llm_usage_user_id_created_at", "user_id", "created_at"),
        # Serves the global rate-limit COUNT and the org-wide monthly spend SUM.
        Index("ix_llm_usage_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    # Correlates the several calls belonging to one agent query.
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Which pipeline step made the call, e.g. "intent_parse" or "generate_response".
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    # The provider and model that actually served the call.
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # NULL when the model has no pricing entry — never coerce to 0.
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="llm_usage")

    def __repr__(self) -> str:
        return (
            f"LlmUsage(id={self.id}, request_id='{self.request_id}', "
            f"stage='{self.stage}', provider='{self.provider}', "
            f"model='{self.model}', input_tokens={self.input_tokens}, "
            f"output_tokens={self.output_tokens}, cost_usd={self.cost_usd})"
        )
