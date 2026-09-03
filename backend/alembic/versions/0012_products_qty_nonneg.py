"""Add non-negative check constraint on products.quantity.

Revision ID: 0012_products_qty_nonneg
Revises: 0011_user_avatar_fields
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0012_products_qty_nonneg"
down_revision: Union[str, None] = "0011_user_avatar_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "ck_products_quantity_non_negative"
CONSTRAINT_SQL = "quantity >= 0"


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("products") as batch_op:
            batch_op.create_check_constraint(CONSTRAINT_NAME, CONSTRAINT_SQL)
        return

    op.create_check_constraint(
        CONSTRAINT_NAME,
        "products",
        CONSTRAINT_SQL,
    )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("products") as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
        return

    op.drop_constraint(CONSTRAINT_NAME, "products", type_="check")
