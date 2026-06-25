def test_audit_logs_for_product_stock_delete_and_restore(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Audit Owner")
    workspace = workspace_factory(owner["headers"], name="Audit Workspace")

    product = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "Audit Product",
            "category": "General",
            "quantity": 5,
            "minimum_quantity": 1,
        },
        headers=owner["headers"],
    ).json()
    client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
        json={
            "movement_type": "entrada",
            "quantity": 2,
            "reason": "Audit movement",
        },
        headers=owner["headers"],
    )
    client.delete(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=owner["headers"],
    )
    client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/restore",
        headers=owner["headers"],
    )

    logs_response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs?limit=100",
        headers=owner["headers"],
    )
    assert logs_response.status_code == 200
    actions = {item["action"] for item in logs_response.json()}
    assert "product.created" in actions
    assert "stock.movement_created" in actions
    assert "product.deleted" in actions
    assert "product.restored" in actions


def test_audit_logs_require_owner_or_admin(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Audit Permission Owner")
    workspace = workspace_factory(owner["headers"], name="Audit Permissions")
    viewer = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "viewer",
    )
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )
    outsider = user_factory(name="Audit Outsider")

    viewer_response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs",
        headers=viewer["headers"],
    )
    assert viewer_response.status_code == 403

    employee_response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs",
        headers=employee["headers"],
    )
    assert employee_response.status_code == 403

    outsider_response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs",
        headers=outsider["headers"],
    )
    assert outsider_response.status_code == 403

    owner_response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs",
        headers=owner["headers"],
    )
    assert owner_response.status_code == 200
