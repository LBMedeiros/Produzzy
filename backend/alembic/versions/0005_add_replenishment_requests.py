"""Add replenishment requests.

Revision ID: 0005_add_replenishment_requests
Revises: 0004_category_soft_delete
Create Date: 2026-07-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_replenishment_requests"
down_revision: Union[str, None] = "0004_category_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "replenishment_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="open",
            nullable=False,
        ),
        sa.Column("quantity_needed", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "quantity_needed > 0",
            name="ck_replenishment_requests_quantity_needed_positive",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'canceled')",
            name="ck_replenishment_requests_status",
        ),
        sa.CheckConstraint(
            "type IN ('purchase', 'production')",
            name="ck_replenishment_requests_type",
        ),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_replenishment_requests_assigned_to_user_id",
        "replenishment_requests",
        ["assigned_to_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_requests_created_by_user_id",
        "replenishment_requests",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_requests_product_id",
        "replenishment_requests",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_requests_status",
        "replenishment_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_requests_workspace_id",
        "replenishment_requests",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_requests_workspace_status",
        "replenishment_requests",
        ["workspace_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_replenishment_requests_workspace_status",
        table_name="replenishment_requests",
    )
    op.drop_index(
        "ix_replenishment_requests_workspace_id",
        table_name="replenishment_requests",
    )
    op.drop_index(
        "ix_replenishment_requests_status",
        table_name="replenishment_requests",
    )
    op.drop_index(
        "ix_replenishment_requests_product_id",
        table_name="replenishment_requests",
    )
    op.drop_index(
        "ix_replenishment_requests_created_by_user_id",
        table_name="replenishment_requests",
    )
    op.drop_index(
        "ix_replenishment_requests_assigned_to_user_id",
        table_name="replenishment_requests",
    )
    op.drop_table("replenishment_requests")
