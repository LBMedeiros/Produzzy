"""Add a cosmetic display title to workspace members.

Revision ID: 0016_workspace_member_title
Revises: 0015_products_category_id
Create Date: 2026-09-21

The title is a label the owner assigns (e.g. "Sócio", "Gerente"); it has no
effect on permissions, which stay on `role`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_workspace_member_title"
down_revision: Union[str, None] = "0015_products_category_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspace_members",
        sa.Column("title", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspace_members", "title")
