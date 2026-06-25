def test_role_permissions_for_products_and_stock(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"], name="Permissions Workspace")

    product_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "Widget",
            "category": "General",
            "quantity": 10,
            "minimum_quantity": 2,
        },
        headers=owner["headers"],
    )
    assert product_response.status_code == 201
    product = product_response.json()

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

    viewer_create_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "Blocked",
            "category": "General",
            "quantity": 1,
            "minimum_quantity": 1,
        },
        headers=viewer["headers"],
    )
    assert viewer_create_response.status_code == 403

    employee_delete_response = client.delete(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=employee["headers"],
    )
    assert employee_delete_response.status_code == 403

    employee_stock_response = client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
        json={
            "movement_type": "entrada",
            "quantity": 5,
            "reason": "Restock",
        },
        headers=employee["headers"],
    )
    assert employee_stock_response.status_code == 201

    outsider = user_factory(name="Outsider")
    outsider_response = client.get(
        f"/workspaces/{workspace['id']}",
        headers=outsider["headers"],
    )
    assert outsider_response.status_code == 403


def test_workspace_isolation_for_products_and_dashboard(
    client,
    user_factory,
    workspace_factory,
):
    owner_a = user_factory(name="Owner A")
    workspace_a = workspace_factory(owner_a["headers"], name="Workspace A")
    owner_b = user_factory(name="Owner B")
    workspace_b = workspace_factory(owner_b["headers"], name="Workspace B")

    product_a = client.post(
        f"/workspaces/{workspace_a['id']}/products",
        json={
            "name": "A Product",
            "category": "General",
            "quantity": 4,
            "minimum_quantity": 1,
        },
        headers=owner_a["headers"],
    ).json()
    product_b = client.post(
        f"/workspaces/{workspace_b['id']}/products",
        json={
            "name": "B Product",
            "category": "General",
            "quantity": 9,
            "minimum_quantity": 1,
        },
        headers=owner_b["headers"],
    ).json()

    list_a_response = client.get(
        f"/workspaces/{workspace_a['id']}/products",
        headers=owner_a["headers"],
    )
    assert list_a_response.status_code == 200
    assert [item["id"] for item in list_a_response.json()] == [product_a["id"]]

    cross_workspace_product_response = client.get(
        f"/workspaces/{workspace_a['id']}/products/{product_b['id']}",
        headers=owner_a["headers"],
    )
    assert cross_workspace_product_response.status_code == 404

    cross_workspace_access_response = client.get(
        f"/workspaces/{workspace_b['id']}/dashboard/summary",
        headers=owner_a["headers"],
    )
    assert cross_workspace_access_response.status_code == 403

    dashboard_response = client.get(
        f"/workspaces/{workspace_a['id']}/dashboard/summary",
        headers=owner_a["headers"],
    )
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["total_products"] == 1
    assert dashboard_response.json()["total_stock_quantity"] == 4
