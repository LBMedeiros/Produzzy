"""Deleting a workspace must remove every row that belongs to it (via DB
ON DELETE CASCADE) and leave other workspaces untouched."""

from sqlalchemy import text

from app.database import SessionLocal


WORKSPACE_SCOPED_TABLES = [
    "audit_logs",
    "categories",
    "products",
    "stock_movements",
    "replenishment_requests",
    "workspace_members",
    "workspace_invites",
    "workspace_invite_links",
]


def _rows_for_workspace(table: str, workspace_id: int) -> int:
    with SessionLocal() as db:
        return db.execute(
            text(f"SELECT count(*) FROM {table} WHERE workspace_id = :wid"),
            {"wid": workspace_id},
        ).scalar_one()


def test_deleting_workspace_cascades_all_related_rows(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"], name="Full workspace")
    wid = workspace["id"]

    # A second workspace acts as the control group.
    other = workspace_factory(owner["headers"], name="Keep me")
    other_category = client.post(
        f"/workspaces/{other['id']}/categories",
        json={"name": "Mantida"},
        headers=owner["headers"],
    )
    assert other_category.status_code == 201

    client.post(
        f"/workspaces/{wid}/categories",
        json={"name": "Insumos"},
        headers=owner["headers"],
    )
    product = client.post(
        f"/workspaces/{wid}/products",
        json={
            "name": "Produto",
            "category": "Insumos",
            "quantity": 5,
            "minimum_quantity": 1,
        },
        headers=owner["headers"],
    ).json()
    client.post(
        f"/workspaces/{wid}/products/{product['id']}/stock",
        json={"movement_type": "entrada", "quantity": 3},
        headers=owner["headers"],
    )
    replenishment = client.post(
        f"/workspaces/{wid}/replenishments",
        json={
            "product_id": product["id"],
            "type": "purchase",
            "quantity_needed": 4,
        },
        headers=owner["headers"],
    )
    assert replenishment.status_code == 201
    client.post(
        f"/workspaces/{wid}/replenishments/{replenishment.json()['id']}/assignees/me",
        headers=owner["headers"],
    )

    # Individual invite + shared invite link + a second member.
    client.post(
        f"/workspaces/{wid}/invites",
        json={"email": "convidado@example.com", "role": "viewer"},
        headers=owner["headers"],
    )
    link = client.post(
        f"/workspaces/{wid}/invite-links",
        json={"role": "viewer"},
        headers=owner["headers"],
    )
    assert link.status_code == 201, link.text
    joiner = user_factory(name="Joiner")
    accepted = client.post(
        f"/invite-links/{link.json()['token']}/accept",
        headers=joiner["headers"],
    )
    assert accepted.status_code == 200, accepted.text
    workspace_member_factory(owner["headers"], wid, "employee")

    for table in WORKSPACE_SCOPED_TABLES:
        assert _rows_for_workspace(table, wid) > 0, f"expected seed rows in {table}"

    deleted = client.delete(f"/workspaces/{wid}", headers=owner["headers"])
    assert deleted.status_code == 204, deleted.text

    for table in WORKSPACE_SCOPED_TABLES:
        assert _rows_for_workspace(table, wid) == 0, f"{table} not cascaded"

    with SessionLocal() as db:
        assert db.execute(
            text("SELECT count(*) FROM workspaces WHERE id = :wid"),
            {"wid": wid},
        ).scalar_one() == 0
        assert db.execute(
            text(
                "SELECT count(*) FROM replenishment_assignees ra "
                "JOIN replenishment_requests rr ON rr.id = ra.replenishment_id "
                "WHERE rr.workspace_id = :wid"
            ),
            {"wid": wid},
        ).scalar_one() == 0
        assert db.execute(
            text(
                "SELECT count(*) FROM workspace_invite_link_acceptances a "
                "JOIN workspace_invite_links l ON l.id = a.invite_link_id "
                "WHERE l.workspace_id = :wid"
            ),
            {"wid": wid},
        ).scalar_one() == 0

    # Control workspace survived.
    assert _rows_for_workspace("categories", other["id"]) == 1
