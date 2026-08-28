"""Add user avatar fields.

Revision ID: 0011_user_avatar_fields
Revises: 0010_workspace_invite_links
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_user_avatar_fields"
down_revision: Union[str, None] = "0010_workspace_invite_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("avatar_public_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_public_id")
    op.drop_column("users", "avatar_url")
