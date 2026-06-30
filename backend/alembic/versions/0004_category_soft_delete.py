"""Add category soft delete and product cascade tracking.

Revision ID: 0004_category_soft_delete
Revises: 0003_add_audit_logs
Create Date: 2026-06-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_category_soft_delete"
down_revision: Union[str, None] = "0003_add_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "categories",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "categories",
        sa.Column("deleted_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_categories_deleted_by_user_id_users",
        "categories",
        "users",
        ["deleted_by_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_categories_deleted_by_user_id",
        "categories",
        ["deleted_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_categories_workspace_is_active",
        "categories",
        ["workspace_id", "is_active"],
        unique=False,
    )

    op.drop_constraint(
        "uq_categories_workspace_name",
        "categories",
        type_="unique",
    )
    op.create_index(
        "uq_categories_workspace_name_active",
        "categories",
        ["workspace_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
        sqlite_where=sa.text("is_active = 1"),
    )

    op.add_column(
        "products",
        sa.Column("deleted_by_category_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_deleted_by_category_id_categories",
        "products",
        "categories",
        ["deleted_by_category_id"],
        ["id"],
    )
    op.create_index(
        "ix_products_deleted_by_category_id",
        "products",
        ["deleted_by_category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_deleted_by_category_id", table_name="products")
    op.drop_constraint(
        "fk_products_deleted_by_category_id_categories",
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "deleted_by_category_id")

    op.drop_index(
        "uq_categories_workspace_name_active",
        table_name="categories",
    )
    op.create_unique_constraint(
        "uq_categories_workspace_name",
        "categories",
        ["workspace_id", "name"],
    )

    op.drop_index("ix_categories_workspace_is_active", table_name="categories")
    op.drop_index("ix_categories_deleted_by_user_id", table_name="categories")
    op.drop_constraint(
        "fk_categories_deleted_by_user_id_users",
        "categories",
        type_="foreignkey",
    )
    op.drop_column("categories", "deleted_by_user_id")
    op.drop_column("categories", "deleted_at")
    op.drop_column("categories", "is_active")
