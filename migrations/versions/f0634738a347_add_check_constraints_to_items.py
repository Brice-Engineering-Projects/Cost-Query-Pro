"""add_check_constraints_to_items

Revision ID: f0634738a347
Revises: b201b4cac42c
Create Date: 2026-06-20 14:08:01.028691

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0634738a347"
down_revision: Union[str, Sequence[str], None] = "b201b4cac42c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add non-negative check constraints to items.unit_price and items.quantity."""
    op.create_check_constraint(
        "ck_items_unit_price_non_negative",
        "items",
        sa.text("unit_price >= 0"),
    )
    op.create_check_constraint(
        "ck_items_quantity_non_negative",
        "items",
        sa.text("quantity >= 0"),
    )


def downgrade() -> None:
    """Remove non-negative check constraints from items."""
    op.drop_constraint("ck_items_unit_price_non_negative", "items", type_="check")
    op.drop_constraint("ck_items_quantity_non_negative", "items", type_="check")
