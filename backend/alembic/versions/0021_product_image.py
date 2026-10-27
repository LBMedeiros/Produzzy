"""Add an optional photo to products.

Revision ID: 0021_product_image
Revises: 0020_workspace_invite_title
Create Date: 2026-10-27

The image lives on Cloudinary (same account as profile photos); the row keeps
its public URL and the public id needed to delete it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0021_product_image"
down_revision: Union[str, None] = "0020_workspace_invite_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(length=500), nullable=True))
    op.add_column(
        "products",
        sa.Column("image_public_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "image_public_id")
    op.drop_column("products", "image_url")
