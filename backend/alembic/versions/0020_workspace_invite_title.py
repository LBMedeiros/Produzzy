"""Let an invite carry the member's display title.

Revision ID: 0020_workspace_invite_title
Revises: 0019_replenishment_messages
Create Date: 2026-10-22

Whoever invites can pick the title (e.g. "Estoquista") the person gets when
the invite is accepted. Like workspace_members.title, it has no effect on
permissions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0020_workspace_invite_title"
down_revision: Union[str, None] = "0019_replenishment_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspace_invites",
        sa.Column("title", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspace_invites", "title")
