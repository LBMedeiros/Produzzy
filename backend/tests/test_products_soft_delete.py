def test_product_soft_delete_restore_and_dashboard(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Soft Delete Owner")
    workspace = workspace_factory(owner["headers"], name="Soft Delete Workspace")

    create_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "Camiseta",
            "category": "Apparel",
            "quantity": 3,
            "minimum_quantity": 5,
        },
        headers=owner["headers"],
    )
    assert create_response.status_code == 201
    product = create_response.json()

    list_response = client.get(
        f"/workspaces/{workspace['id']}/products",
        headers=owner["headers"],
    )
    assert [item["id"] for item in list_response.json()] == [product["id"]]

    dashboard_before = client.get(
        f"/workspaces/{workspace['id']}/dashboard/summary",
        headers=owner["headers"],
    ).json()
    assert dashboard_before["total_products"] == 1
    assert dashboard_before["low_stock_products"] == 1
    assert dashboard_before["total_stock_quantity"] == 3

    delete_response = client.delete(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=owner["headers"],
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["is_active"] is False

    active_list_response = client.get(
        f"/workspaces/{workspace['id']}/products",
        headers=owner["headers"],
    )
    assert active_list_response.status_code == 200
    assert active_list_response.json() == []

    deleted_list_response = client.get(
        f"/workspaces/{workspace['id']}/products?status=deleted",
        headers=owner["headers"],
    )
    assert deleted_list_response.status_code == 200
    assert [item["id"] for item in deleted_list_response.json()] == [product["id"]]

    deleted_detail_response = client.get(
        (
            f"/workspaces/{workspace['id']}/products/{product['id']}"
            "?include_deleted=true"
        ),
        headers=owner["headers"],
    )
    assert deleted_detail_response.status_code == 200
    assert deleted_detail_response.json()["is_active"] is False

    stock_response = client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
        json={
            "movement_type": "entrada",
            "quantity": 1,
            "reason": "Should fail",
        },
        headers=owner["headers"],
    )
    assert stock_response.status_code == 400

    dashboard_after_delete = client.get(
        f"/workspaces/{workspace['id']}/dashboard/summary",
        headers=owner["headers"],
    ).json()
    assert dashboard_after_delete["total_products"] == 0
    assert dashboard_after_delete["low_stock_products"] == 0
    assert dashboard_after_delete["total_stock_quantity"] == 0

    restore_response = client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/restore",
        headers=owner["headers"],
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["is_active"] is True


def test_low_stock_uses_strict_minimum_rule(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Strict Stock Owner")
    workspace = workspace_factory(owner["headers"], name="Strict Stock Workspace")

    for quantity in (51, 50, 49, 1, 0):
        response = client.post(
            f"/workspaces/{workspace['id']}/products",
            json={
                "name": f"Produto {quantity}",
                "category": "Teste",
                "quantity": quantity,
                "minimum_quantity": 50,
            },
            headers=owner["headers"],
        )
        assert response.status_code == 201

    low_stock_response = client.get(
        f"/workspaces/{workspace['id']}/products/low-stock?limit=100",
        headers=owner["headers"],
    )
    assert low_stock_response.status_code == 200
    assert [item["quantity"] for item in low_stock_response.json()] == [1, 49]

    dashboard_response = client.get(
        f"/workspaces/{workspace['id']}/dashboard/summary",
        headers=owner["headers"],
    )
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["low_stock_products"] == 2


def test_restore_blocks_when_another_active_product_has_same_name(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Restore Owner")
    workspace = workspace_factory(owner["headers"], name="Restore Workspace")
    product_payload = {
        "name": "Camiseta",
        "category": "Apparel",
        "quantity": 1,
        "minimum_quantity": 1,
    }

    old_product = client.post(
        f"/workspaces/{workspace['id']}/products",
        json=product_payload,
        headers=owner["headers"],
    ).json()
    client.delete(
        f"/workspaces/{workspace['id']}/products/{old_product['id']}",
        headers=owner["headers"],
    )
    new_product = client.post(
        f"/workspaces/{workspace['id']}/products",
        json=product_payload,
        headers=owner["headers"],
    ).json()

    blocked_restore = client.post(
        f"/workspaces/{workspace['id']}/products/{old_product['id']}/restore",
        headers=owner["headers"],
    )
    assert blocked_restore.status_code == 400

    client.delete(
        f"/workspaces/{workspace['id']}/products/{new_product['id']}",
        headers=owner["headers"],
    )
    restore_response = client.post(
        f"/workspaces/{workspace['id']}/products/{old_product['id']}/restore",
        headers=owner["headers"],
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["id"] == old_product["id"]
