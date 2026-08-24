"""Add Google auth fields to users.

Revision ID: 0008_add_google_auth_fields
Revises: 0007_add_stocked_status
Create Date: 2026-08-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_add_google_auth_fields"
down_revision: Union[str, None] = "0007_add_stocked_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "auth_provider",
                sa.String(length=30),
                server_default="password",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("provider_user_id", sa.String(length=255), nullable=True)
        )
        batch_op.alter_column(
            "hashed_password",
            existing_type=sa.String(length=255),
            nullable=True,
        )

    op.alter_column("users", "auth_provider", server_default=None)
    op.create_index(
        "ix_users_provider_user_id",
        "users",
        ["provider_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_users_auth_provider_provider_user_id",
        "users",
        ["auth_provider", "provider_user_id"],
        unique=True,
        postgresql_where=sa.text("provider_user_id IS NOT NULL"),
        sqlite_where=sa.text("provider_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_users_auth_provider_provider_user_id",
        table_name="users",
        postgresql_where=sa.text("provider_user_id IS NOT NULL"),
        sqlite_where=sa.text("provider_user_id IS NOT NULL"),
    )
    op.drop_index("ix_users_provider_user_id", table_name="users")

    op.execute(
        """
        UPDATE users
        SET hashed_password = 'google-auth-user-without-local-password'
        WHERE hashed_password IS NULL
        """
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "hashed_password",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.drop_column("provider_user_id")
        batch_op.drop_column("auth_provider")
