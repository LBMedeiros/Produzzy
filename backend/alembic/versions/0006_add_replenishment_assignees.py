"""Add multiple replenishment assignees.

Revision ID: 0006_add_replenishment_assignees
Revises: 0005_add_replenishment_requests
Create Date: 2026-07-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_add_replenishment_assignees"
down_revision: Union[str, None] = "0005_add_replenishment_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "replenishment_assignees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("replenishment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["replenishment_id"],
            ["replenishment_requests.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "replenishment_id",
            "user_id",
            name="uq_replenishment_assignees_request_user",
        ),
    )
    op.create_index(
        "ix_replenishment_assignees_assigned_by_user_id",
        "replenishment_assignees",
        ["assigned_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_assignees_replenishment_id",
        "replenishment_assignees",
        ["replenishment_id"],
        unique=False,
    )
    op.create_index(
        "ix_replenishment_assignees_user_id",
        "replenishment_assignees",
        ["user_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO replenishment_assignees (
            replenishment_id,
            user_id,
            assigned_by_user_id,
            created_at
        )
        SELECT
            id,
            assigned_to_user_id,
            created_by_user_id,
            created_at
        FROM replenishment_requests
        WHERE assigned_to_user_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_replenishment_assignees_user_id",
        table_name="replenishment_assignees",
    )
    op.drop_index(
        "ix_replenishment_assignees_replenishment_id",
        table_name="replenishment_assignees",
    )
    op.drop_index(
        "ix_replenishment_assignees_assigned_by_user_id",
        table_name="replenishment_assignees",
    )
    op.drop_table("replenishment_assignees")
