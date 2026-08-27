"""Add active replenishment unique index.

Revision ID: 0009_active_replenishment_uq
Revises: 0008_add_google_auth_fields
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_active_replenishment_uq"
down_revision: Union[str, None] = "0008_add_google_auth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE_REPLENISHMENT_WHERE = sa.text(
    "status IN ('open', 'in_progress', 'completed')"
)


def upgrade() -> None:
    op.create_index(
        "uq_replenishment_requests_active_product",
        "replenishment_requests",
        ["workspace_id", "product_id"],
        unique=True,
        postgresql_where=ACTIVE_REPLENISHMENT_WHERE,
        sqlite_where=ACTIVE_REPLENISHMENT_WHERE,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_replenishment_requests_active_product",
        table_name="replenishment_requests",
    )
