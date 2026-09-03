"""Convert audit_logs.metadata to JSONB on Postgres.

Revision ID: 0013_audit_metadata_jsonb
Revises: 0012_products_qty_nonneg
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0013_audit_metadata_jsonb"
down_revision: Union[str, None] = "0012_products_qty_nonneg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.alter_column(
        "audit_logs",
        "metadata",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="metadata::jsonb",
        existing_nullable=True,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.alter_column(
        "audit_logs",
        "metadata",
        type_=postgresql.JSON(astext_type=sa.Text()),
        postgresql_using="metadata::json",
        existing_nullable=True,
    )
