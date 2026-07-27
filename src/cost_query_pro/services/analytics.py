"""src/cost_query_pro/services/analytics.py

Step 3 of the Secure Query Pipeline: compute summary statistics from
matching Item records. Only the resulting CostSummary is passed to the
LLM — raw records never leave the application infrastructure.
"""

import logging
import statistics as stats_lib

from cost_query_pro.core.errors import AppError
from cost_query_pro.models import Item
from cost_query_pro.schemas.agent import CostSummary

logger = logging.getLogger(__name__)


def compute_summary(items: list[Item]) -> CostSummary:
    """Compute aggregated price statistics from a list of Items.

    Uses Python's stdlib statistics module — no additional dependencies.

    Args:
        items: List of Item ORM objects from run_search().

    Returns:
        CostSummary with record_count, median, average, min, and max prices.

    Raises:
        AppError: code='NO_RESULTS', status=404 if items is empty.
    """
    if not items:
        raise AppError(
            "NO_RESULTS",
            "No matching records found for your query. Try broadening the search criteria.",
            404,
        )

    prices = [float(item.unit_price) for item in items]

    summary = CostSummary(
        record_count=len(prices),
        median_price=stats_lib.median(prices),
        average_price=stats_lib.mean(prices),
        minimum_price=min(prices),
        maximum_price=max(prices),
    )

    logger.info(
        "compute_summary: %d records, median=%.2f, avg=%.2f, range=[%.2f, %.2f]",
        summary.record_count,
        summary.median_price,
        summary.average_price,
        summary.minimum_price,
        summary.maximum_price,
    )
    return summary
