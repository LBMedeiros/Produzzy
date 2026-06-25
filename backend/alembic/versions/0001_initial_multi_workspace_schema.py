"""Initial multi-workspace schema.

Revision ID: 0001_initial_multi_workspace
Revises:
Create Date: 2026-06-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_multi_workspace"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_name", "workspaces", ["name"], unique=False)
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"], unique=False)

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_members_workspace_user",
        ),
    )
    op.create_index(
        "ix_workspace_members_user_id",
        "workspace_members",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_members_workspace_id",
        "workspace_members",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "workspace_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("accepted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_invites_accepted_by_user_id",
        "workspace_invites",
        ["accepted_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invites_created_by_user_id",
        "workspace_invites",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invites_email",
        "workspace_invites",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invites_status",
        "workspace_invites",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invites_token",
        "workspace_invites",
        ["token"],
        unique=True,
    )
    op.create_index(
        "ix_workspace_invites_workspace_id",
        "workspace_invites",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "uq_workspace_invites_pending_email",
        "workspace_invites",
        ["workspace_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_categories_workspace_name",
        ),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=False)
    op.create_index(
        "ix_categories_workspace_id",
        "categories",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("minimum_quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_products_workspace_name",
        ),
    )
    op.create_index("ix_products_category", "products", ["category"], unique=False)
    op.create_index("ix_products_name", "products", ["name"], unique=False)
    op.create_index(
        "ix_products_workspace_id",
        "products",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stock_movements_product_id",
        "stock_movements",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_user_id",
        "stock_movements",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_workspace_id",
        "stock_movements",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stock_movements_workspace_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_user_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_product_id", table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index("ix_products_workspace_id", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_categories_workspace_id", table_name="categories")
    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")

    op.drop_index(
        "uq_workspace_invites_pending_email",
        table_name="workspace_invites",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_index("ix_workspace_invites_workspace_id", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_token", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_status", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_email", table_name="workspace_invites")
    op.drop_index(
        "ix_workspace_invites_created_by_user_id",
        table_name="workspace_invites",
    )
    op.drop_index(
        "ix_workspace_invites_accepted_by_user_id",
        table_name="workspace_invites",
    )
    op.drop_table("workspace_invites")

    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_table("workspace_members")

    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
    op.drop_index("ix_workspaces_name", table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
