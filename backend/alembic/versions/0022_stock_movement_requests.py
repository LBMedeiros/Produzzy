"""Add stock movement requests and their conversation messages.

The Solicitante asks for an entrada/saída; Operação and up approve or reject.

Revision ID: 0022_stock_movement_requests
Revises: 0021_product_image
Create Date: 2026-11-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0022_stock_movement_requests"
down_revision: Union[str, None] = "0021_product_image"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_movement_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("stock_movement_id", sa.Integer(), nullable=True),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_quantity", sa.Integer(), nullable=False),
        sa.Column("approved_quantity", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("review_note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "movement_type IN ('entrada', 'saida')",
            name="ck_stock_movement_requests_movement_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'canceled')",
            name="ck_stock_movement_requests_status",
        ),
        sa.CheckConstraint(
            "requested_quantity > 0",
            name="ck_stock_movement_requests_requested_quantity_positive",
        ),
        sa.CheckConstraint(
            "approved_quantity IS NULL OR approved_quantity > 0",
            name="ck_stock_movement_requests_approved_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["stock_movement_id"],
            ["stock_movements.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "id",
        "workspace_id",
        "product_id",
        "requested_by_user_id",
        "reviewed_by_user_id",
        "stock_movement_id",
    ):
        op.create_index(
            f"ix_stock_movement_requests_{column}",
            "stock_movement_requests",
            [column],
            unique=False,
        )
    op.create_index(
        "ix_stock_movement_requests_workspace_status",
        "stock_movement_requests",
        ["workspace_id", "status"],
        unique=False,
    )

    op.create_table(
        "stock_movement_request_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["stock_movement_requests.id"],
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
    for column in ("id", "request_id", "workspace_id", "user_id", "created_at"):
        op.create_index(
            f"ix_stock_movement_request_messages_{column}",
            "stock_movement_request_messages",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in ("created_at", "user_id", "workspace_id", "request_id", "id"):
        op.drop_index(
            f"ix_stock_movement_request_messages_{column}",
            table_name="stock_movement_request_messages",
        )
    op.drop_table("stock_movement_request_messages")

    op.drop_index(
        "ix_stock_movement_requests_workspace_status",
        table_name="stock_movement_requests",
    )
    for column in (
        "stock_movement_id",
        "reviewed_by_user_id",
        "requested_by_user_id",
        "product_id",
        "workspace_id",
        "id",
    ):
        op.drop_index(
            f"ix_stock_movement_requests_{column}",
            table_name="stock_movement_requests",
        )
    op.drop_table("stock_movement_requests")
