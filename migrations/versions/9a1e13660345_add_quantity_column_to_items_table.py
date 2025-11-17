"""Add quantity column to items table

Revision ID: 9a1e13660345
Revises: b36567dabb22
Create Date: 2025-10-24 23:30:40.955714
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a1e13660345"
down_revision: Union[str, Sequence[str], None] = "b36567dabb22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("items", sa.Column("quantity", sa.Integer(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("items", "quantity")
