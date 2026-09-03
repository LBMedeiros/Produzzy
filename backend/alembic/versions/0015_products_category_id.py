"""Link products to categories by id (keeping the denormalized name).

Revision ID: 0015_products_category_id
Revises: 0014_workspace_fk_cascade
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015_products_category_id"
down_revision: Union[str, None] = "0014_workspace_fk_cascade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAME = "fk_products_category_id_categories"
IX_NAME = "ix_products_category_id"


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("category_id", sa.Integer(), nullable=True),
    )
    op.create_index(IX_NAME, "products", ["category_id"])
    op.create_foreign_key(
        FK_NAME,
        "products",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Backfill: prefer the active category with the same name in the same
    # workspace; fall back to any same-name category (e.g. soft-deleted).
    op.execute(
        """
        UPDATE products p
        SET category_id = c.id
        FROM categories c
        WHERE c.workspace_id = p.workspace_id
          AND c.name = p.category
          AND c.is_active = true
        """
    )
    op.execute(
        """
        UPDATE products p
        SET category_id = sub.id
        FROM (
            SELECT DISTINCT ON (workspace_id, name) id, workspace_id, name
            FROM categories
            ORDER BY workspace_id, name, is_active DESC, id ASC
        ) sub
        WHERE p.category_id IS NULL
          AND sub.workspace_id = p.workspace_id
          AND sub.name = p.category
        """
    )


def downgrade() -> None:
    op.drop_constraint(FK_NAME, "products", type_="foreignkey")
    op.drop_index(IX_NAME, table_name="products")
    op.drop_column("products", "category_id")
