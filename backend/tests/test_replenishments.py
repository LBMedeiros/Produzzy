def create_product(client, workspace, account, name="Produto"):
    response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": name,
            "category": "Insumos",
            "quantity": 2,
            "minimum_quantity": 10,
        },
        headers=account["headers"],
    )
    assert response.status_code == 201, response.text

    return response.json()


def create_replenishment(
    client,
    workspace,
    account,
    product,
    request_type="purchase",
    quantity=8,
):
    response = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": product["id"],
            "type": request_type,
            "quantity_needed": quantity,
            "notes": "Reposição necessária",
        },
        headers=account["headers"],
    )
    assert response.status_code == 201, response.text

    return response.json()


def test_create_purchase_and_production_replenishments(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Replenishment Owner")
    workspace = workspace_factory(owner["headers"], name="Replenishments")
    purchase_product = create_product(client, workspace, owner)
    production_product = create_product(
        client,
        workspace,
        owner,
        name="Produto para produção",
    )

    purchase = create_replenishment(
        client,
        workspace,
        owner,
        purchase_product,
        request_type="purchase",
    )
    production = create_replenishment(
        client,
        workspace,
        owner,
        production_product,
        request_type="production",
        quantity=5,
    )

    assert purchase["type"] == "purchase"
    assert purchase["status"] == "open"
    assert purchase["product_name"] == purchase_product["name"]
    assert purchase["product_category"] == purchase_product["category"]
    assert purchase["current_quantity"] == purchase_product["quantity"]
    assert purchase["minimum_quantity"] == purchase_product["minimum_quantity"]
    assert purchase["created_by_name"] == owner["user"]["name"]
    assert purchase["completed_at"] is None
    assert production["type"] == "production"
    assert production["quantity_needed"] == 5


def test_replenishment_validates_product_workspace_and_quantity(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Validation Owner")
    workspace = workspace_factory(owner["headers"], name="Validation Workspace")
    other_workspace = workspace_factory(
        owner["headers"],
        name="Other Validation Workspace",
    )
    other_product = create_product(
        client,
        other_workspace,
        owner,
        name="Produto externo",
    )

    cross_workspace_response = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": other_product["id"],
            "type": "purchase",
            "quantity_needed": 3,
        },
        headers=owner["headers"],
    )
    assert cross_workspace_response.status_code == 404

    product = create_product(client, workspace, owner)

    for invalid_quantity in (0, -1):
        invalid_quantity_response = client.post(
            f"/workspaces/{workspace['id']}/replenishments",
            json={
                "product_id": product["id"],
                "type": "production",
                "quantity_needed": invalid_quantity,
            },
            headers=owner["headers"],
        )
        assert invalid_quantity_response.status_code == 422


def test_list_filter_and_update_replenishments(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Flow Owner")
    workspace = workspace_factory(owner["headers"], name="Flow Workspace")
    open_product = create_product(client, workspace, owner)
    completed_product = create_product(
        client,
        workspace,
        owner,
        name="Produto concluído",
    )
    open_request = create_replenishment(client, workspace, owner, open_product)
    completed_request = create_replenishment(
        client,
        workspace,
        owner,
        completed_product,
        request_type="production",
    )

    in_progress_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{open_request['id']}"
        ),
        json={"status": "in_progress"},
        headers=owner["headers"],
    )
    assert in_progress_response.status_code == 200
    assert in_progress_response.json()["status"] == "in_progress"
    assert in_progress_response.json()["completed_at"] is None

    completed_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{completed_request['id']}"
        ),
        json={"status": "completed"},
        headers=owner["headers"],
    )
    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "completed"
    assert completed_response.json()["completed_at"] is not None

    product_after_completion = client.get(
        f"/workspaces/{workspace['id']}/products/{completed_product['id']}",
        headers=owner["headers"],
    ).json()
    assert product_after_completion["quantity"] == completed_product["quantity"]

    default_list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments",
        headers=owner["headers"],
    )
    assert default_list_response.status_code == 200
    assert [item["id"] for item in default_list_response.json()] == [
        open_request["id"]
    ]

    completed_list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments?status=completed",
        headers=owner["headers"],
    )
    assert completed_list_response.status_code == 200
    assert [item["id"] for item in completed_list_response.json()] == [
        completed_request["id"]
    ]

    canceled_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{open_request['id']}"
        ),
        json={"status": "canceled"},
        headers=owner["headers"],
    )
    assert canceled_response.status_code == 200
    assert canceled_response.json()["status"] == "canceled"

    canceled_list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments?status=canceled",
        headers=owner["headers"],
    )
    assert canceled_list_response.status_code == 200
    assert [item["id"] for item in canceled_list_response.json()] == [
        open_request["id"]
    ]

    all_list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments?status=all",
        headers=owner["headers"],
    )
    assert all_list_response.status_code == 200
    assert {item["id"] for item in all_list_response.json()} == {
        open_request["id"],
        completed_request["id"],
    }

    audit_response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs?limit=100",
        headers=owner["headers"],
    )
    actions = {item["action"] for item in audit_response.json()}
    assert "replenishment.created" in actions
    assert "replenishment.updated" in actions
    assert "replenishment.completed" in actions
    assert "replenishment.canceled" in actions


def test_replenishment_permissions(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Permission Owner")
    workspace = workspace_factory(owner["headers"], name="Permission Workspace")
    product = create_product(client, workspace, owner)
    employee_product = create_product(
        client,
        workspace,
        owner,
        name="Produto do employee",
    )
    request_item = create_replenishment(client, workspace, owner, product)
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
    outsider = user_factory(name="Replenishment Outsider")

    viewer_list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments",
        headers=viewer["headers"],
    )
    assert viewer_list_response.status_code == 200

    viewer_detail_response = client.get(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        headers=viewer["headers"],
    )
    assert viewer_detail_response.status_code == 200

    viewer_create_response = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": product["id"],
            "type": "purchase",
            "quantity_needed": 1,
        },
        headers=viewer["headers"],
    )
    assert viewer_create_response.status_code == 403

    viewer_update_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        json={"status": "in_progress"},
        headers=viewer["headers"],
    )
    assert viewer_update_response.status_code == 403

    employee_create_response = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": employee_product["id"],
            "type": "production",
            "quantity_needed": 4,
        },
        headers=employee["headers"],
    )
    assert employee_create_response.status_code == 201

    employee_update_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        json={"status": "in_progress"},
        headers=employee["headers"],
    )
    assert employee_update_response.status_code == 200

    employee_edit_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        json={"quantity_needed": 99},
        headers=employee["headers"],
    )
    assert employee_edit_response.status_code == 403

    outsider_list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments",
        headers=outsider["headers"],
    )
    assert outsider_list_response.status_code == 403

    outsider_create_response = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": product["id"],
            "type": "purchase",
            "quantity_needed": 2,
        },
        headers=outsider["headers"],
    )
    assert outsider_create_response.status_code == 403


def test_replenishment_blocks_active_duplicates_and_allows_terminal_history(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Lifecycle Owner")
    workspace = workspace_factory(owner["headers"], name="Lifecycle Workspace")
    product = create_product(client, workspace, owner)

    first_request = create_replenishment(client, workspace, owner, product)
    duplicate_response = client.post(
        f"/workspaces/{workspace['id']}/replenishments",
        json={
            "product_id": product["id"],
            "type": "production",
            "quantity_needed": 4,
        },
        headers=owner["headers"],
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "Já existe uma necessidade ativa para este produto."
    )

    canceled_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{first_request['id']}"
        ),
        json={"status": "canceled"},
        headers=owner["headers"],
    )
    assert canceled_response.status_code == 200

    second_request = create_replenishment(client, workspace, owner, product)
    completed_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{second_request['id']}"
        ),
        json={"status": "completed"},
        headers=owner["headers"],
    )
    assert completed_response.status_code == 200

    stocked_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{second_request['id']}"
        ),
        json={"status": "stocked"},
        headers=owner["headers"],
    )
    assert stocked_response.status_code == 200
    assert stocked_response.json()["status"] == "stocked"
    assert stocked_response.json()["completed_at"] is not None

    third_request = create_replenishment(client, workspace, owner, product)
    assert third_request["status"] == "open"

    completed_list = client.get(
        f"/workspaces/{workspace['id']}/replenishments?status=completed",
        headers=owner["headers"],
    )
    stocked_list = client.get(
        f"/workspaces/{workspace['id']}/replenishments?status=stocked",
        headers=owner["headers"],
    )
    assert completed_list.status_code == 200
    assert completed_list.json() == []
    assert stocked_list.status_code == 200
    assert [item["id"] for item in stocked_list.json()] == [
        second_request["id"]
    ]


def test_stock_entry_marks_completed_replenishment_as_stocked(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Stock Entry Owner")
    workspace = workspace_factory(owner["headers"], name="Stock Entry Workspace")
    product = create_product(client, workspace, owner)
    request_item = create_replenishment(client, workspace, owner, product)

    completed_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        json={"status": "completed"},
        headers=owner["headers"],
    )
    assert completed_response.status_code == 200

    movement_response = client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
        json={
            "movement_type": "entrada",
            "quantity": 7,
            "reason": "Entrada real da reposição",
            "replenishment_request_id": request_item["id"],
        },
        headers=owner["headers"],
    )
    assert movement_response.status_code == 201, movement_response.text
    assert movement_response.json()["quantity_before"] == product["quantity"]
    assert movement_response.json()["quantity_after"] == product["quantity"] + 7

    stocked_detail = client.get(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        headers=owner["headers"],
    )
    assert stocked_detail.status_code == 200
    assert stocked_detail.json()["status"] == "stocked"

    completed_list = client.get(
        f"/workspaces/{workspace['id']}/replenishments?status=completed",
        headers=owner["headers"],
    )
    assert completed_list.json() == []

    audit_response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs?limit=100",
        headers=owner["headers"],
    )
    assert "replenishment.stocked" in {
        item["action"] for item in audit_response.json()
    }


def test_employee_can_assume_and_leave_replenishment(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Assignee Owner")
    workspace = workspace_factory(owner["headers"], name="Assignee Workspace")
    product = create_product(client, workspace, owner)
    request_item = create_replenishment(client, workspace, owner, product)
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )

    assign_response = client.post(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}/assignees/me"
        ),
        headers=employee["headers"],
    )
    assert assign_response.status_code == 200, assign_response.text
    assigned_request = assign_response.json()
    assert assigned_request["assigned_to_user_id"] == employee["user"]["id"]
    assert assigned_request["assignees"] == [
        {
            "id": employee["user"]["id"],
            "name": employee["user"]["name"],
            "email": employee["user"]["email"],
            "role": "employee",
        }
    ]

    duplicate_response = client.post(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}/assignees/me"
        ),
        headers=employee["headers"],
    )
    assert duplicate_response.status_code == 400

    list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments",
        headers=employee["headers"],
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["assignees"][0]["id"] == employee["user"]["id"]

    unassign_response = client.delete(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}/assignees/me"
        ),
        headers=employee["headers"],
    )
    assert unassign_response.status_code == 200
    assert unassign_response.json()["assigned_to_user_id"] is None
    assert unassign_response.json()["assignees"] == []


def test_viewer_and_outsider_cannot_assume_replenishment(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Restricted Assignee Owner")
    workspace = workspace_factory(
        owner["headers"],
        name="Restricted Assignee Workspace",
    )
    product = create_product(client, workspace, owner)
    request_item = create_replenishment(client, workspace, owner, product)
    viewer = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "viewer",
    )
    outsider = user_factory(name="Assignee Outsider")
    endpoint = (
        f"/workspaces/{workspace['id']}/replenishments/"
        f"{request_item['id']}/assignees/me"
    )

    viewer_response = client.post(endpoint, headers=viewer["headers"])
    assert viewer_response.status_code == 403

    outsider_response = client.post(endpoint, headers=outsider["headers"])
    assert outsider_response.status_code == 403


def test_owner_manages_multiple_assignees_without_workspace_leaks(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Multiple Assignee Owner")
    workspace = workspace_factory(owner["headers"], name="Multiple Assignees")
    product = create_product(client, workspace, owner)
    request_item = create_replenishment(client, workspace, owner, product)
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )
    admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )

    for account in (employee, admin):
        assign_response = client.post(
            (
                f"/workspaces/{workspace['id']}/replenishments/"
                f"{request_item['id']}/assignees/{account['user']['id']}"
            ),
            headers=owner["headers"],
        )
        assert assign_response.status_code == 200, assign_response.text

    detail_response = client.get(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        headers=owner["headers"],
    )
    assert detail_response.status_code == 200
    assert {assignee["id"] for assignee in detail_response.json()["assignees"]} == {
        employee["user"]["id"],
        admin["user"]["id"],
    }

    other_owner = user_factory(name="Other Assignee Owner")
    other_workspace = workspace_factory(
        other_owner["headers"],
        name="Other Assignee Workspace",
    )
    other_employee = workspace_member_factory(
        other_owner["headers"],
        other_workspace["id"],
        "employee",
    )
    cross_member_response = client.post(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}/assignees/{other_employee['user']['id']}"
        ),
        headers=owner["headers"],
    )
    assert cross_member_response.status_code == 400

    other_product = create_product(
        client,
        other_workspace,
        other_owner,
        name="Outro produto",
    )
    other_request = create_replenishment(
        client,
        other_workspace,
        other_owner,
        other_product,
    )
    client.post(
        (
            f"/workspaces/{other_workspace['id']}/replenishments/"
            f"{other_request['id']}/assignees/me"
        ),
        headers=other_employee["headers"],
    )

    own_list_response = client.get(
        f"/workspaces/{workspace['id']}/replenishments",
        headers=owner["headers"],
    )
    returned_assignee_ids = {
        assignee["id"]
        for item in own_list_response.json()
        for assignee in item["assignees"]
    }
    assert other_employee["user"]["id"] not in returned_assignee_ids

    remove_response = client.delete(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}/assignees/{employee['user']['id']}"
        ),
        headers=owner["headers"],
    )
    assert remove_response.status_code == 200
    assert {item["id"] for item in remove_response.json()["assignees"]} == {
        admin["user"]["id"]
    }


def test_completed_replenishment_rejects_assignee_update_via_patch(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Closed Assignee Owner")
    workspace = workspace_factory(owner["headers"], name="Closed Assignee")
    product = create_product(client, workspace, owner)
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )
    admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )
    request_item = create_replenishment(
        client,
        workspace,
        owner,
        product,
    )

    assign_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        json={"assigned_to_user_id": employee["user"]["id"]},
        headers=owner["headers"],
    )
    assert assign_response.status_code == 200, assign_response.text
    assert assign_response.json()["assigned_to_user_id"] == employee["user"]["id"]

    completed_response = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        json={"status": "completed"},
        headers=owner["headers"],
    )
    assert completed_response.status_code == 200, completed_response.text

    blocked_update = client.patch(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        json={"assigned_to_user_id": admin["user"]["id"]},
        headers=owner["headers"],
    )

    assert blocked_update.status_code == 400
    assert blocked_update.json()["detail"] == (
        "Não é possível alterar responsáveis de uma necessidade "
        "concluída, estocada ou cancelada."
    )

    detail_response = client.get(
        (
            f"/workspaces/{workspace['id']}/replenishments/"
            f"{request_item['id']}"
        ),
        headers=owner["headers"],
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["assigned_to_user_id"] == employee["user"]["id"]
    assert {assignee["id"] for assignee in detail["assignees"]} == {
        employee["user"]["id"]
    }
