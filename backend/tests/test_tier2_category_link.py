"""products.category_id keeps the product<->category link stable across
renames and drives soft-delete by id instead of name matching."""


def _make(client, headers, workspace_id):
    category = client.post(
        f"/workspaces/{workspace_id}/categories",
        json={"name": "Insumos"},
        headers=headers,
    ).json()
    product = client.post(
        f"/workspaces/{workspace_id}/products",
        json={
            "name": "Parafuso",
            "category": "Insumos",
            "quantity": 10,
            "minimum_quantity": 1,
        },
        headers=headers,
    ).json()
    return category, product


def test_create_product_links_category_id(
    client, user_factory, workspace_factory
):
    owner = user_factory()
    workspace = workspace_factory(owner["headers"])
    category, product = _make(client, owner["headers"], workspace["id"])

    assert product["category_id"] == category["id"]
    assert product["category"] == "Insumos"


def test_renaming_category_propagates_to_products(
    client, user_factory, workspace_factory
):
    owner = user_factory()
    workspace = workspace_factory(owner["headers"])
    category, product = _make(client, owner["headers"], workspace["id"])

    renamed = client.patch(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        json={"name": "Matéria-prima"},
        headers=owner["headers"],
    )
    assert renamed.status_code == 200, renamed.text

    fetched = client.get(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=owner["headers"],
    ).json()
    assert fetched["category"] == "Matéria-prima"
    assert fetched["category_id"] == category["id"]


def test_deleting_category_soft_deletes_linked_products_by_id(
    client, user_factory, workspace_factory
):
    owner = user_factory()
    workspace = workspace_factory(owner["headers"])
    category, product = _make(client, owner["headers"], workspace["id"])

    # Rename so a stale name match could no longer find the product.
    client.patch(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        json={"name": "Renomeada"},
        headers=owner["headers"],
    )

    deleted = client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=owner["headers"],
    )
    assert deleted.status_code in (200, 204), deleted.text

    fetched = client.get(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        params={"include_deleted": "true"},
        headers=owner["headers"],
    ).json()
    assert fetched["is_active"] is False
    assert fetched["deleted_by_category_id"] == category["id"]
