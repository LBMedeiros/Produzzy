"""Add an optional backup recovery e-mail to users.

Revision ID: 0018_users_recovery_email
Revises: 0017_users_email_verified
Create Date: 2026-09-25

Users may register a secondary e-mail. Once confirmed, the password-reset link
is also sent to it, so losing access to the primary inbox is recoverable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_users_recovery_email"
down_revision: Union[str, None] = "0017_users_email_verified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("recovery_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "recovery_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("users", "recovery_email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "recovery_email_verified")
    op.drop_column("users", "recovery_email")
