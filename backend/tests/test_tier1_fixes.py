"""Regression tests for the Tier 1 stability fixes."""


def _create_product(client, workspace, account, name="Produto", quantity=5):
    response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": name,
            "category": "Insumos",
            "quantity": quantity,
            "minimum_quantity": 1,
        },
        headers=account["headers"],
    )
    assert response.status_code == 201, response.text

    return response.json()


def test_delete_workspace_with_replenishment_succeeds(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"], name="To Delete")
    product = _create_product(client, workspace, owner)

    replenishment = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": product["id"],
            "type": "purchase",
            "quantity_needed": 3,
            "assigned_to_user_id": owner["user"]["id"],
        },
        headers=owner["headers"],
    )
    assert replenishment.status_code == 201, replenishment.text

    deleted = client.delete(
        f"/workspaces/{workspace['id']}",
        headers=owner["headers"],
    )
    assert deleted.status_code == 204, deleted.text

    gone = client.get(
        f"/workspaces/{workspace['id']}",
        headers=owner["headers"],
    )
    assert gone.status_code in (403, 404)


def test_stock_adjustment_to_zero_is_allowed(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"], name="Stock")
    product = _create_product(client, workspace, owner, quantity=7)

    response = client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
        json={"movement_type": "ajuste", "quantity": 0, "reason": "Contagem"},
        headers=owner["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["quantity_after"] == 0


def test_stock_entry_with_zero_quantity_is_rejected(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"], name="Stock")
    product = _create_product(client, workspace, owner)

    response = client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
        json={"movement_type": "entrada", "quantity": 0},
        headers=owner["headers"],
    )
    assert response.status_code == 400, response.text
