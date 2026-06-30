def create_category(client, workspace_id, headers, name):
    response = client.post(
        f"/workspaces/{workspace_id}/categories",
        json={
            "description": f"Descrição de {name}",
            "name": name,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_product(client, workspace_id, headers, name, category):
    response = client.post(
        f"/workspaces/{workspace_id}/products",
        json={
            "category": category,
            "minimum_quantity": 1,
            "name": name,
            "quantity": 5,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_category_soft_delete_cascades_and_restore_is_selective(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Category Cascade Owner")
    workspace = workspace_factory(owner["headers"], name="Category Cascade")
    category = create_category(
        client,
        workspace["id"],
        owner["headers"],
        "Especialidades",
    )
    previously_deleted = create_product(
        client,
        workspace["id"],
        owner["headers"],
        "Produto antigo",
        category["name"],
    )
    cascaded_product = create_product(
        client,
        workspace["id"],
        owner["headers"],
        "Produto ativo",
        category["name"],
    )
    movement_response = client.post(
        (
            f"/workspaces/{workspace['id']}/products/"
            f"{cascaded_product['id']}/stock"
        ),
        json={
            "movement_type": "entrada",
            "quantity": 2,
            "reason": "Movimentação preservada",
        },
        headers=owner["headers"],
    )
    assert movement_response.status_code == 201
    client.delete(
        f"/workspaces/{workspace['id']}/products/{previously_deleted['id']}",
        headers=owner["headers"],
    )

    delete_response = client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=owner["headers"],
    )
    assert delete_response.status_code == 200, delete_response.text
    deleted_category = delete_response.json()
    assert deleted_category["is_active"] is False
    assert deleted_category["deleted_at"] is not None
    assert deleted_category["deleted_by_user_id"] == owner["user"]["id"]

    repeated_delete = client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=owner["headers"],
    )
    assert repeated_delete.status_code == 200
    assert repeated_delete.json()["is_active"] is False

    active_categories = client.get(
        f"/workspaces/{workspace['id']}/categories?status=active",
        headers=owner["headers"],
    ).json()
    deleted_categories = client.get(
        f"/workspaces/{workspace['id']}/categories?status=deleted",
        headers=owner["headers"],
    ).json()
    all_categories = client.get(
        f"/workspaces/{workspace['id']}/categories?status=all",
        headers=owner["headers"],
    ).json()
    assert active_categories == []
    assert [item["id"] for item in deleted_categories] == [category["id"]]
    assert [item["id"] for item in all_categories] == [category["id"]]

    persisted_category = client.get(
        (
            f"/workspaces/{workspace['id']}/categories/{category['id']}"
            "?include_deleted=true"
        ),
        headers=owner["headers"],
    )
    assert persisted_category.status_code == 200

    deleted_products = client.get(
        f"/workspaces/{workspace['id']}/products?status=deleted&limit=100",
        headers=owner["headers"],
    ).json()
    deleted_products_by_id = {item["id"]: item for item in deleted_products}
    assert (
        deleted_products_by_id[cascaded_product["id"]]["deleted_by_category_id"]
        == category["id"]
    )
    assert (
        deleted_products_by_id[previously_deleted["id"]]["deleted_by_category_id"]
        is None
    )
    movements_after_delete = client.get(
        (
            f"/workspaces/{workspace['id']}/products/"
            f"{cascaded_product['id']}/stock-movements"
        ),
        headers=owner["headers"],
    )
    assert movements_after_delete.status_code == 200
    assert len(movements_after_delete.json()) == 1

    restore_response = client.post(
        f"/workspaces/{workspace['id']}/categories/{category['id']}/restore",
        headers=owner["headers"],
    )
    assert restore_response.status_code == 200, restore_response.text
    restore_data = restore_response.json()
    assert restore_data["category"]["is_active"] is True
    assert restore_data["restored_products_count"] == 1
    assert restore_data["skipped_products_count"] == 0

    active_products = client.get(
        f"/workspaces/{workspace['id']}/products?status=active&limit=100",
        headers=owner["headers"],
    ).json()
    assert [item["id"] for item in active_products] == [cascaded_product["id"]]

    still_deleted = client.get(
        f"/workspaces/{workspace['id']}/products?status=deleted&limit=100",
        headers=owner["headers"],
    ).json()
    assert [item["id"] for item in still_deleted] == [previously_deleted["id"]]

    logs = client.get(
        f"/workspaces/{workspace['id']}/audit-logs?limit=100",
        headers=owner["headers"],
    ).json()
    actions = [item["action"] for item in logs]
    assert "category.deleted" in actions
    assert "category.restored" in actions
    assert actions.count("product.deleted") == 2
    assert "product.restored" in actions


def test_soft_delete_category_without_products(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Empty Category Owner")
    workspace = workspace_factory(owner["headers"], name="Empty Category")
    category = create_category(
        client,
        workspace["id"],
        owner["headers"],
        "Sem produtos",
    )

    response = client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_category_restore_skips_conflicting_product_and_blocks_name_conflict(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Category Conflict Owner")
    workspace = workspace_factory(owner["headers"], name="Category Conflicts")
    category = create_category(
        client,
        workspace["id"],
        owner["headers"],
        "Conflitante",
    )
    old_product = create_product(
        client,
        workspace["id"],
        owner["headers"],
        "Mesmo produto",
        category["name"],
    )
    client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=owner["headers"],
    )
    create_product(
        client,
        workspace["id"],
        owner["headers"],
        "Mesmo produto",
        "Outra categoria",
    )

    restore_response = client.post(
        f"/workspaces/{workspace['id']}/categories/{category['id']}/restore",
        headers=owner["headers"],
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["restored_products_count"] == 0
    assert restore_response.json()["skipped_products_count"] == 1

    old_product_response = client.get(
        (
            f"/workspaces/{workspace['id']}/products/{old_product['id']}"
            "?include_deleted=true"
        ),
        headers=owner["headers"],
    )
    assert old_product_response.json()["is_active"] is False
    assert (
        old_product_response.json()["deleted_by_category_id"] == category["id"]
    )

    client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=owner["headers"],
    )
    create_category(
        client,
        workspace["id"],
        owner["headers"],
        category["name"],
    )
    blocked_restore = client.post(
        f"/workspaces/{workspace['id']}/categories/{category['id']}/restore",
        headers=owner["headers"],
    )
    assert blocked_restore.status_code == 400
    assert (
        blocked_restore.json()["detail"]
        == "Another active category with this name already exists in this workspace."
    )


def test_category_delete_restore_permissions_and_workspace_isolation(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Category Permission Owner")
    workspace = workspace_factory(owner["headers"], name="Category Permissions")
    category = create_category(
        client,
        workspace["id"],
        owner["headers"],
        "Protegida",
    )
    admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )
    viewer = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "viewer",
    )

    for account in [employee, viewer]:
        denied_delete = client.delete(
            f"/workspaces/{workspace['id']}/categories/{category['id']}",
            headers=account["headers"],
        )
        assert denied_delete.status_code == 403

    admin_delete = client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=admin["headers"],
    )
    assert admin_delete.status_code == 200

    for account in [employee, viewer]:
        denied_restore = client.post(
            f"/workspaces/{workspace['id']}/categories/{category['id']}/restore",
            headers=account["headers"],
        )
        assert denied_restore.status_code == 403

    admin_restore = client.post(
        f"/workspaces/{workspace['id']}/categories/{category['id']}/restore",
        headers=admin["headers"],
    )
    assert admin_restore.status_code == 200

    outsider = user_factory(name="Category Outsider")
    outsider_response = client.delete(
        f"/workspaces/{workspace['id']}/categories/{category['id']}",
        headers=outsider["headers"],
    )
    assert outsider_response.status_code == 403

    other_owner = user_factory(name="Other Category Owner")
    other_workspace = workspace_factory(
        other_owner["headers"],
        name="Other Category Workspace",
    )
    other_category = create_category(
        client,
        other_workspace["id"],
        other_owner["headers"],
        "Outra categoria",
    )
    cross_workspace_delete = client.delete(
        f"/workspaces/{workspace['id']}/categories/{other_category['id']}",
        headers=owner["headers"],
    )
    assert cross_workspace_delete.status_code == 404
    cross_workspace_restore = client.post(
        (
            f"/workspaces/{workspace['id']}/categories/"
            f"{other_category['id']}/restore"
        ),
        headers=owner["headers"],
    )
    assert cross_workspace_restore.status_code == 404
