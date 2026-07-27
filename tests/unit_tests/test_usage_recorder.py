"""tests/unit_tests/test_usage_recorder.py

Unit tests for LLM cost accounting: the pricing table, the metering provider
wrapper, and persistence of usage rows.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from cost_query_pro.config.pricing import USD_PER_MTOK, estimate_cost_usd
from cost_query_pro.models.llm_usage import LlmUsage
from cost_query_pro.models.user import User
from cost_query_pro.services.llm_provider import (
    CompletionResult,
    LLMProvider,
    MeteredProvider,
)
from cost_query_pro.services.usage_recorder import record_usage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    text: str = "answer",
    provider: str = "claude",
    model: str = "claude-sonnet-4-6",
    input_tokens: int = 1000,
    output_tokens: int = 500,
) -> CompletionResult:
    return CompletionResult(
        text=text,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


@pytest.fixture
def usage_user(db_session):
    user = User(username="usage_user", password_hash="x", is_admin=False)
    db_session.add(user)
    db_session.commit()
    return user


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def test_known_model_prices_input_and_output_separately(self):
        # claude-sonnet-4-6 is $3.00 / $15.00 per million tokens.
        cost = estimate_cost_usd("claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.00)

    def test_scales_linearly_below_one_million(self):
        cost = estimate_cost_usd("claude-sonnet-4-6", 1000, 500)
        assert cost == pytest.approx((1000 * 3.0 + 500 * 15.0) / 1_000_000)

    def test_zero_tokens_is_zero_not_none(self):
        assert estimate_cost_usd("claude-sonnet-4-6", 0, 0) == 0.0

    def test_unknown_model_returns_none_not_zero(self):
        """None keeps 'unpriced' distinguishable from 'free' in spend totals."""
        assert "totally-made-up-model" not in USD_PER_MTOK
        assert estimate_cost_usd("totally-made-up-model", 1000, 500) is None


# ---------------------------------------------------------------------------
# MeteredProvider
# ---------------------------------------------------------------------------


class TestMeteredProvider:
    def test_passes_result_through_unchanged(self):
        inner = MagicMock(spec=LLMProvider)
        inner.name = "claude"
        expected = _make_result()
        inner.complete.return_value = expected

        provider = MeteredProvider(inner=inner)
        assert provider.complete([{"role": "user", "content": "hi"}]) is expected

    def test_accumulates_one_entry_per_call(self):
        inner = MagicMock(spec=LLMProvider)
        inner.name = "claude"
        inner.complete.return_value = _make_result()

        provider = MeteredProvider(inner=inner)
        assert provider.calls == []
        provider.complete([{"role": "user", "content": "a"}])
        provider.complete([{"role": "user", "content": "b"}])
        assert len(provider.calls) == 2

    def test_exposes_inner_provider_name(self):
        inner = MagicMock(spec=LLMProvider)
        inner.name = "fallback"
        assert MeteredProvider(inner=inner).name == "fallback"

    def test_forwards_keyword_arguments(self):
        inner = MagicMock(spec=LLMProvider)
        inner.name = "claude"
        inner.complete.return_value = _make_result()

        MeteredProvider(inner=inner).complete(
            [{"role": "user", "content": "hi"}],
            system="sys",
            max_tokens=512,
            request_id="req-1",
        )
        _, kwargs = inner.complete.call_args
        assert kwargs["system"] == "sys"
        assert kwargs["max_tokens"] == 512
        assert kwargs["request_id"] == "req-1"


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------


class TestRecordUsage:
    def test_writes_one_row_per_completion(self, db_session, usage_user):
        record_usage(
            db_session,
            user_id=usage_user.id,
            request_id="req-abc",
            calls=[_make_result(), _make_result()],
        )
        rows = db_session.query(LlmUsage).filter_by(request_id="req-abc").all()
        assert len(rows) == 2

    def test_labels_stages_in_pipeline_order(self, db_session, usage_user):
        record_usage(
            db_session,
            user_id=usage_user.id,
            request_id="req-stages",
            calls=[_make_result(), _make_result()],
        )
        rows = (
            db_session.query(LlmUsage)
            .filter_by(request_id="req-stages")
            .order_by(LlmUsage.id)
            .all()
        )
        assert [r.stage for r in rows] == ["intent_parse", "generate_response"]

    def test_extra_calls_are_labelled_positionally_not_dropped(
        self, db_session, usage_user
    ):
        """A future tool-use loop makes an unbounded number of calls."""
        record_usage(
            db_session,
            user_id=usage_user.id,
            request_id="req-many",
            calls=[_make_result() for _ in range(4)],
        )
        rows = (
            db_session.query(LlmUsage)
            .filter_by(request_id="req-many")
            .order_by(LlmUsage.id)
            .all()
        )
        assert [r.stage for r in rows] == [
            "intent_parse",
            "generate_response",
            "call_2",
            "call_3",
        ]

    def test_persists_tokens_and_cost(self, db_session, usage_user):
        record_usage(
            db_session,
            user_id=usage_user.id,
            request_id="req-cost",
            calls=[_make_result(input_tokens=1000, output_tokens=500)],
        )
        row = db_session.query(LlmUsage).filter_by(request_id="req-cost").one()
        assert row.input_tokens == 1000
        assert row.output_tokens == 500
        assert float(row.cost_usd) == pytest.approx(0.0105)

    def test_unpriced_model_records_null_cost_with_tokens_intact(
        self, db_session, usage_user
    ):
        record_usage(
            db_session,
            user_id=usage_user.id,
            request_id="req-unpriced",
            calls=[_make_result(model="some-future-model")],
        )
        row = db_session.query(LlmUsage).filter_by(request_id="req-unpriced").one()
        assert row.cost_usd is None
        assert row.input_tokens == 1000

    def test_attributes_the_provider_that_actually_served(self, db_session, usage_user):
        """On failover the row must name OpenAI, not the configured Claude."""
        record_usage(
            db_session,
            user_id=usage_user.id,
            request_id="req-failover",
            calls=[_make_result(provider="openai", model="gpt-4o")],
        )
        row = db_session.query(LlmUsage).filter_by(request_id="req-failover").one()
        assert row.provider == "openai"
        assert row.model == "gpt-4o"

    def test_no_calls_writes_nothing(self, db_session, usage_user):
        assert (
            record_usage(
                db_session, user_id=usage_user.id, request_id="req-empty", calls=[]
            )
            == []
        )
        assert db_session.query(LlmUsage).filter_by(request_id="req-empty").count() == 0

    def test_write_failure_does_not_propagate(self, usage_user):
        """Accounting must never turn a successful answer into a failed request."""
        broken = MagicMock()
        broken.commit.side_effect = RuntimeError("db is down")

        assert (
            record_usage(
                broken, user_id=1, request_id="req-boom", calls=[_make_result()]
            )
            == []
        )
        broken.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# created_at constraint
#
# created_at is the window column for the Phase 2 cost controls: rate limits
# COUNT over a time window and the spend cap SUMs over the calendar month. A
# NULL never satisfies a range predicate, so an untimestamped row would drop
# silently out of both. These tests pin the NOT NULL that makes those
# aggregates trustworthy (migration a3f5c81e7b24).
# ---------------------------------------------------------------------------


class TestCreatedAtConstraint:
    def test_column_is_not_nullable_in_migrated_schema(self, db_session):
        """The migrated table, not just the model, rejects a null timestamp."""
        columns = sa_inspect(db_session.get_bind()).get_columns("llm_usage")
        created_at = next(c for c in columns if c["name"] == "created_at")
        assert created_at["nullable"] is False

    def test_server_default_populates_created_at(self, db_session, usage_user):
        """Inserting without a timestamp still works — the default fills it."""
        row = LlmUsage(
            user_id=usage_user.id,
            request_id="req-default",
            stage="intent_parse",
            provider="claude",
            model="claude-sonnet-4-6",
            input_tokens=10,
            output_tokens=5,
        )
        db_session.add(row)
        db_session.commit()

        assert row.created_at is not None

    def test_explicit_null_created_at_is_rejected(self, db_session, usage_user):
        """An explicit NULL is refused rather than silently escaping the window.

        This goes through Core rather than the ORM on purpose: when a column
        has a server_default, SQLAlchemy omits a None-valued attribute from
        the INSERT so the default fires, which means the ORM cannot produce a
        NULL here at all. Only raw SQL exercises the database constraint.
        """
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    "INSERT INTO llm_usage "
                    "(user_id, request_id, stage, provider, model, "
                    " input_tokens, output_tokens, created_at) "
                    "VALUES (:uid, 'req-null', 'intent_parse', 'claude', "
                    " 'claude-sonnet-4-6', 10, 5, NULL)"
                ),
                {"uid": usage_user.id},
            )

        db_session.rollback()
