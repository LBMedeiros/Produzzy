"""Add email_verified flag to users (blocks login until confirmed).

Revision ID: 0017_users_email_verified
Revises: 0016_workspace_member_title
Create Date: 2026-09-25

New password accounts start unverified and must confirm their e-mail before
logging in. Existing accounts are grandfathered in as verified so this deploy
does not lock anyone out. Google accounts are always created verified.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_users_email_verified"
down_revision: Union[str, None] = "0016_workspace_member_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Grandfather every existing account so this deploy does not lock anyone out.
    op.execute("UPDATE users SET email_verified = true")
    # New rows are set explicitly by the app; drop the DB-side default.
    op.alter_column("users", "email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_verified")
