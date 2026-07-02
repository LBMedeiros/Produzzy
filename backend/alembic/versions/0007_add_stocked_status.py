"""Add stocked replenishment status.

Revision ID: 0007_add_stocked_status
Revises: 0006_add_replenishment_assignees
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0007_add_stocked_status"
down_revision: Union[str, None] = "0006_add_replenishment_assignees"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_replenishment_requests_status",
        "replenishment_requests",
        type_="check",
    )
    op.create_check_constraint(
        "ck_replenishment_requests_status",
        "replenishment_requests",
        (
            "status IN "
            "('open', 'in_progress', 'completed', 'stocked', 'canceled')"
        ),
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE replenishment_requests
        SET status = 'completed'
        WHERE status = 'stocked'
        """
    )
    op.drop_constraint(
        "ck_replenishment_requests_status",
        "replenishment_requests",
        type_="check",
    )
    op.create_check_constraint(
        "ck_replenishment_requests_status",
        "replenishment_requests",
        "status IN ('open', 'in_progress', 'completed', 'canceled')",
    )
