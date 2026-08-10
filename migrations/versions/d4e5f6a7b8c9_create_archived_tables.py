"""create archived project/item tables

Revision ID: d4e5f6a7b8c9
Revises: a3f5c81e7b24
Create Date: 2026-07-30

Fixes Phase 1 audit C-2 by creating non-conflicting archival tables:
- archived_projects
- archived_items

Also corrects archived timestamp semantics (DateTime) and preserves item upload
lineage via archived_items.upload_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "a3f5c81e7b24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "archived_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_name", sa.String(), nullable=False),
        sa.Column("project_number", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "archived_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("purged_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["purged_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_archived_projects_id"),
        "archived_projects",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_archived_projects_project_name"),
        "archived_projects",
        ["project_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_archived_projects_project_number"),
        "archived_projects",
        ["project_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_archived_projects_state"),
        "archived_projects",
        ["state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_archived_projects_year"),
        "archived_projects",
        ["year"],
        unique=False,
    )

    op.create_table(
        "archived_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("item_description", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=True),
        sa.Column(
            "archived_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name="ck_archived_items_unit_price_non_negative",
        ),
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_archived_items_quantity_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["archived_projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["upload_id"],
            ["upload_history.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_archived_items_id"),
        "archived_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_archived_items_item_description"),
        "archived_items",
        ["item_description"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_archived_items_item_description"), table_name="archived_items"
    )
    op.drop_index(op.f("ix_archived_items_id"), table_name="archived_items")
    op.drop_table("archived_items")

    op.drop_index(op.f("ix_archived_projects_year"), table_name="archived_projects")
    op.drop_index(op.f("ix_archived_projects_state"), table_name="archived_projects")
    op.drop_index(
        op.f("ix_archived_projects_project_number"), table_name="archived_projects"
    )
    op.drop_index(
        op.f("ix_archived_projects_project_name"), table_name="archived_projects"
    )
    op.drop_index(op.f("ix_archived_projects_id"), table_name="archived_projects")
    op.drop_table("archived_projects")
