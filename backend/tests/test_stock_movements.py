def test_list_workspace_stock_movements_with_product_and_user_data(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Movement Owner")
    workspace = workspace_factory(owner["headers"], name="Movement Workspace")
    other_owner = user_factory(name="Other Movement Owner")
    other_workspace = workspace_factory(
        other_owner["headers"],
        name="Other Movement Workspace",
    )

    product_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "Linha Azul",
            "category": "Insumos",
            "quantity": 10,
            "minimum_quantity": 2,
        },
        headers=owner["headers"],
    )
    assert product_response.status_code == 201
    product = product_response.json()

    other_product = client.post(
        f"/workspaces/{other_workspace['id']}/products",
        json={
            "name": "Outro Produto",
            "category": "Insumos",
            "quantity": 5,
            "minimum_quantity": 1,
        },
        headers=other_owner["headers"],
    ).json()

    for quantity in [1, 2]:
        movement_response = client.post(
            f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
            json={
                "movement_type": "entrada",
                "quantity": quantity,
                "reason": f"Reposição {quantity}",
            },
            headers=owner["headers"],
        )
        assert movement_response.status_code == 201

    client.post(
        f"/workspaces/{other_workspace['id']}/products/{other_product['id']}/stock",
        json={
            "movement_type": "entrada",
            "quantity": 3,
            "reason": "Outro workspace",
        },
        headers=other_owner["headers"],
    )

    viewer = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "viewer",
    )

    list_response = client.get(
        f"/workspaces/{workspace['id']}/stock-movements?limit=1",
        headers=viewer["headers"],
    )
    assert list_response.status_code == 200
    page_one = list_response.json()
    assert len(page_one) == 1
    assert page_one[0]["workspace_id"] == workspace["id"]
    assert page_one[0]["product_id"] == product["id"]
    assert page_one[0]["product_name"] == "Linha Azul"
    assert page_one[0]["user_name"] == owner["user"]["name"]

    page_two_response = client.get(
        f"/workspaces/{workspace['id']}/stock-movements?page=2&limit=1",
        headers=viewer["headers"],
    )
    assert page_two_response.status_code == 200
    assert len(page_two_response.json()) == 1

    outsider_response = client.get(
        f"/workspaces/{workspace['id']}/stock-movements",
        headers=other_owner["headers"],
    )
    assert outsider_response.status_code == 403
