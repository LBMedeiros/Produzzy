"""Add product soft delete fields.

Revision ID: 0002_product_soft_delete
Revises: 0001_initial_multi_workspace
Create Date: 2026-06-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_product_soft_delete"
down_revision: Union[str, None] = "0001_initial_multi_workspace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("deleted_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_deleted_by_user_id_users",
        "products",
        "users",
        ["deleted_by_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_products_deleted_by_user_id",
        "products",
        ["deleted_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_products_workspace_is_active",
        "products",
        ["workspace_id", "is_active"],
        unique=False,
    )

    op.drop_constraint(
        "uq_products_workspace_name",
        "products",
        type_="unique",
    )
    op.create_index(
        "uq_products_workspace_name_active",
        "products",
        ["workspace_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_products_workspace_name_active", table_name="products")
    op.create_unique_constraint(
        "uq_products_workspace_name",
        "products",
        ["workspace_id", "name"],
    )

    op.drop_index("ix_products_workspace_is_active", table_name="products")
    op.drop_index("ix_products_deleted_by_user_id", table_name="products")
    op.drop_constraint(
        "fk_products_deleted_by_user_id_users",
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "deleted_by_user_id")
    op.drop_column("products", "deleted_at")
    op.drop_column("products", "is_active")
