def create_product(client, workspace_id, headers, name, quantity, minimum=10):
    response = client.post(
        f"/workspaces/{workspace_id}/products",
        json={
            "name": name,
            "category": "General",
            "quantity": quantity,
            "minimum_quantity": minimum,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    return response.json()


def create_category(client, workspace_id, headers, name):
    response = client.post(
        f"/workspaces/{workspace_id}/categories",
        json={
            "name": name,
            "description": "",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    return response.json()


def test_dashboard_consolidated_counts_attention_activity_and_isolation(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Dashboard Owner")
    workspace = workspace_factory(owner["headers"], name="Dashboard Workspace")
    other_owner = user_factory(name="Other Dashboard Owner")
    other_workspace = workspace_factory(
        other_owner["headers"],
        name="Other Dashboard Workspace",
    )

    create_category(client, workspace["id"], owner["headers"], "General")
    create_category(client, workspace["id"], owner["headers"], "Packaging")
    create_category(client, other_workspace["id"], other_owner["headers"], "Other")

    products = {
        "zero_free": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Zero Free",
            0,
            0,
        ),
        "zero_high": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Zero High",
            0,
            10,
        ),
        "low_one": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Low One",
            1,
            10,
        ),
        "low_two": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Low Two",
            2,
            10,
        ),
        "equal_min": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Equal Minimum",
            10,
            10,
        ),
        "healthy": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Healthy",
            30,
            10,
        ),
        "low_three": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Low Three",
            3,
            10,
        ),
        "low_four": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Low Four",
            4,
            10,
        ),
        "low_five": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Low Five",
            5,
            10,
        ),
        "low_six": create_product(
            client,
            workspace["id"],
            owner["headers"],
            "Low Six",
            6,
            10,
        ),
    }
    create_product(
        client,
        other_workspace["id"],
        other_owner["headers"],
        "Other Zero",
        0,
        20,
    )

    for movement_type, quantity in [("entrada", 5), ("saida", 3)]:
        response = client.post(
            (
                f"/workspaces/{workspace['id']}/products/"
                f"{products['healthy']['id']}/stock"
            ),
            json={
                "movement_type": movement_type,
                "quantity": quantity,
                "reason": "Dashboard test movement",
            },
            headers=owner["headers"],
        )
        assert response.status_code == 201, response.text

    response = client.get(
        f"/workspaces/{workspace['id']}/dashboard",
        headers=owner["headers"],
    )

    assert response.status_code == 200, response.text
    data = response.json()
    summary = data["summary"]
    assert summary["total_products"] == 10
    assert summary["total_categories"] == 2
    assert summary["low_stock_products"] == 6
    assert summary["out_of_stock_products"] == 2
    assert summary["total_stock_quantity"] == 63
    assert summary["total_stock_movements"] == 2

    attention_names = [item["name"] for item in data["attention_products"]]
    assert attention_names == [
        "Zero Free",
        "Zero High",
        "Low One",
        "Low Two",
        "Low Three",
        "Low Four",
    ]
    assert len(data["recent_activity"]) == 6
    assert all(
        item["workspace_id"] == workspace["id"]
        for item in data["recent_activity"]
    )
    recent_ids = [item["id"] for item in data["recent_activity"]]
    assert recent_ids == sorted(recent_ids, reverse=True)

    outsider_response = client.get(
        f"/workspaces/{workspace['id']}/dashboard",
        headers=other_owner["headers"],
    )
    assert outsider_response.status_code == 403


def test_dashboard_summary_keeps_legacy_endpoint_with_new_out_of_stock_count(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Dashboard Summary Owner")
    workspace = workspace_factory(owner["headers"], name="Summary Workspace")
    create_product(
        client,
        workspace["id"],
        owner["headers"],
        "Summary Zero",
        0,
        5,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/dashboard/summary",
        headers=owner["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["out_of_stock_products"] == 1


def test_dashboard_does_not_expose_recent_activity_to_viewer(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Dashboard Activity Owner")
    workspace = workspace_factory(owner["headers"], name="Activity Workspace")
    viewer = workspace_member_factory(owner["headers"], workspace["id"], "viewer")
    create_product(
        client,
        workspace["id"],
        owner["headers"],
        "Viewer Visible Product",
        4,
        10,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/dashboard",
        headers=viewer["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["summary"]["total_products"] == 1
    assert response.json()["recent_activity"] == []
