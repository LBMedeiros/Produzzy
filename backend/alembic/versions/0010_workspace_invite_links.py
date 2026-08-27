"""Add workspace invite links.

Revision ID: 0010_workspace_invite_links
Revises: 0009_active_replenishment_uq
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_workspace_invite_links"
down_revision: Union[str, None] = "0009_active_replenishment_uq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_invite_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role = 'viewer'",
            name="ck_workspace_invite_links_role_viewer",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'expired', 'revoked')",
            name="ck_workspace_invite_links_status",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_invite_links_created_by_user_id",
        "workspace_invite_links",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invite_links_status",
        "workspace_invite_links",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invite_links_token",
        "workspace_invite_links",
        ["token"],
        unique=True,
    )
    op.create_index(
        "ix_workspace_invite_links_workspace_id",
        "workspace_invite_links",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "workspace_invite_link_acceptances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invite_link_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invite_link_id"],
            ["workspace_invite_links.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "invite_link_id",
            "user_id",
            name="uq_workspace_invite_link_acceptances_link_user",
        ),
    )
    op.create_index(
        "ix_workspace_invite_link_acceptances_invite_link_id",
        "workspace_invite_link_acceptances",
        ["invite_link_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invite_link_acceptances_user_id",
        "workspace_invite_link_acceptances",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_invite_link_acceptances_user_id",
        table_name="workspace_invite_link_acceptances",
    )
    op.drop_index(
        "ix_workspace_invite_link_acceptances_invite_link_id",
        table_name="workspace_invite_link_acceptances",
    )
    op.drop_table("workspace_invite_link_acceptances")

    op.drop_index(
        "ix_workspace_invite_links_workspace_id",
        table_name="workspace_invite_links",
    )
    op.drop_index(
        "ix_workspace_invite_links_token",
        table_name="workspace_invite_links",
    )
    op.drop_index(
        "ix_workspace_invite_links_status",
        table_name="workspace_invite_links",
    )
    op.drop_index(
        "ix_workspace_invite_links_created_by_user_id",
        table_name="workspace_invite_links",
    )
    op.drop_table("workspace_invite_links")
