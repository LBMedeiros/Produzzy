def create_product(
    client,
    workspace,
    account,
    name="Parafuso Azul",
    category="Ferragens",
):
    response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": name,
            "category": category,
            "quantity": 4,
            "minimum_quantity": 10,
        },
        headers=account["headers"],
    )
    assert response.status_code == 201, response.text

    return response.json()


def create_replenishment(client, workspace, account, product):
    response = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": product["id"],
            "type": "purchase",
            "quantity_needed": 6,
        },
        headers=account["headers"],
    )
    assert response.status_code == 201, response.text

    return response.json()


def test_workspace_search_returns_scoped_products_and_replenishments(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Search Owner")
    workspace = workspace_factory(owner["headers"], name="Search Workspace")
    product = create_product(client, workspace, owner)
    replenishment = create_replenishment(client, workspace, owner, product)

    other_owner = user_factory(name="Other Search Owner")
    other_workspace = workspace_factory(
        other_owner["headers"],
        name="Other Search Workspace",
    )
    other_product = create_product(
        client,
        other_workspace,
        other_owner,
        name="Parafuso Externo",
    )
    create_replenishment(client, other_workspace, other_owner, other_product)

    search_response = client.get(
        f"/workspaces/{workspace['id']}/search?q=Parafuso",
        headers=owner["headers"],
    )
    assert search_response.status_code == 200, search_response.text
    result = search_response.json()
    assert [item["id"] for item in result["products"]] == [product["id"]]
    assert [item["id"] for item in result["replenishments"]] == [
        replenishment["id"]
    ]

    code_response = client.get(
        f"/workspaces/{workspace['id']}/search?q={str(product['id']).zfill(9)}",
        headers=owner["headers"],
    )
    assert code_response.status_code == 200
    assert code_response.json()["products"][0]["id"] == product["id"]

    status_response = client.get(
        f"/workspaces/{workspace['id']}/search?q=necessario",
        headers=owner["headers"],
    )
    assert status_response.status_code == 200
    assert status_response.json()["replenishments"][0]["id"] == replenishment["id"]

    forbidden_response = client.get(
        f"/workspaces/{workspace['id']}/search?q=Parafuso",
        headers=other_owner["headers"],
    )
    assert forbidden_response.status_code == 403
