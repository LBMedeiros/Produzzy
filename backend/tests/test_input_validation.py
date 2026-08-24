def test_product_text_fields_are_trimmed_and_reject_blank_values(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Product Validation Owner")
    workspace = workspace_factory(owner["headers"], name="Product Validation")

    create_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "  Product A  ",
            "category": "  Supplies  ",
            "quantity": 2,
            "minimum_quantity": 1,
        },
        headers=owner["headers"],
    )
    assert create_response.status_code == 201, create_response.text
    product = create_response.json()
    assert product["name"] == "Product A"
    assert product["category"] == "Supplies"

    blank_name_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "   ",
            "category": "Supplies",
            "quantity": 1,
            "minimum_quantity": 1,
        },
        headers=owner["headers"],
    )
    assert blank_name_response.status_code == 422

    blank_category_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "Product B",
            "category": "   ",
            "quantity": 1,
            "minimum_quantity": 1,
        },
        headers=owner["headers"],
    )
    assert blank_category_response.status_code == 422

    update_response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        json={"name": "  Product A Updated  ", "category": "  Storage  "},
        headers=owner["headers"],
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["name"] == "Product A Updated"
    assert update_response.json()["category"] == "Storage"

    null_name_response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        json={"name": None},
        headers=owner["headers"],
    )
    assert null_name_response.status_code == 422

    blank_update_response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        json={"category": "   "},
        headers=owner["headers"],
    )
    assert blank_update_response.status_code == 422


def test_category_name_is_trimmed_and_rejects_blank_values(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Category Validation Owner")
    workspace = workspace_factory(owner["headers"], name="Category Validation")

    create_response = client.post(
        f"/workspaces/{workspace['id']}/categories",
        json={"name": "  Materials  ", "description": "Tracked inputs"},
        headers=owner["headers"],
    )
    assert create_response.status_code == 201, create_response.text
    category = create_response.json()
    assert category["name"] == "Materials"

    blank_create_response = client.post(
        f"/workspaces/{workspace['id']}/categories",
        json={"name": "   "},
        headers=owner["headers"],
    )
    assert blank_create_response.status_code == 422

    update_response = client.patch(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        json={"name": "  Raw Materials  "},
        headers=owner["headers"],
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["name"] == "Raw Materials"

    null_update_response = client.patch(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        json={"name": None},
        headers=owner["headers"],
    )
    assert null_update_response.status_code == 422

    blank_update_response = client.patch(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        json={"name": "   "},
        headers=owner["headers"],
    )
    assert blank_update_response.status_code == 422
