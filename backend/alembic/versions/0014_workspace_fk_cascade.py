"""Add ON DELETE CASCADE to the workspace ownership chain.

Revision ID: 0014_workspace_fk_cascade
Revises: 0013_audit_metadata_jsonb
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0014_workspace_fk_cascade"
down_revision: Union[str, None] = "0013_audit_metadata_jsonb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, constraint_name, [local_cols], referred_table, ondelete)
CASCADE_FKS = [
    ("workspace_members", "workspace_members_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
    ("workspace_invites", "workspace_invites_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
    ("workspace_invite_links", "workspace_invite_links_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
    ("workspace_invite_link_acceptances",
     "workspace_invite_link_acceptances_invite_link_id_fkey",
     ["invite_link_id"], "workspace_invite_links", "CASCADE"),
    ("categories", "categories_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
    ("products", "products_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
    ("products", "fk_products_deleted_by_category_id_categories",
     ["deleted_by_category_id"], "categories", "SET NULL"),
    ("stock_movements", "stock_movements_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
    ("stock_movements", "stock_movements_product_id_fkey",
     ["product_id"], "products", "CASCADE"),
    ("replenishment_requests", "replenishment_requests_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
    ("replenishment_requests", "replenishment_requests_product_id_fkey",
     ["product_id"], "products", "CASCADE"),
    ("replenishment_assignees", "replenishment_assignees_replenishment_id_fkey",
     ["replenishment_id"], "replenishment_requests", "CASCADE"),
    ("audit_logs", "audit_logs_workspace_id_fkey",
     ["workspace_id"], "workspaces", "CASCADE"),
]


def _rebuild(with_ondelete: bool) -> None:
    for table, name, local_cols, ref_table, ondelete in CASCADE_FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name,
            table,
            ref_table,
            local_cols,
            ["id"],
            ondelete=ondelete if with_ondelete else None,
        )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    _rebuild(with_ondelete=True)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    _rebuild(with_ondelete=False)
