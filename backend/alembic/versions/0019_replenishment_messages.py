"""Add replenishment handoff messages (chat).

Revision ID: 0019_replenishment_messages
Revises: 0018_users_recovery_email
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0019_replenishment_messages"
down_revision: Union[str, None] = "0018_users_recovery_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "replenishment_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("replenishment_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["replenishment_id"],
            ["replenishment_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_replenishment_messages_replenishment_id",
        "replenishment_messages",
        ["replenishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_messages_workspace_id",
        "replenishment_messages",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_messages_user_id",
        "replenishment_messages",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_messages_created_at",
        "replenishment_messages",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_replenishment_messages_created_at",
        table_name="replenishment_messages",
    )
    op.drop_index(
        "ix_replenishment_messages_user_id",
        table_name="replenishment_messages",
    )
    op.drop_index(
        "ix_replenishment_messages_workspace_id",
        table_name="replenishment_messages",
    )
    op.drop_index(
        "ix_replenishment_messages_replenishment_id",
        table_name="replenishment_messages",
    )
    op.drop_table("replenishment_messages")
