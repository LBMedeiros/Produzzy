"""Stock movement requests: the Solicitante asks, Operação and up decide."""
from uuid import uuid4


def add_member(client, user_factory, owner_headers, workspace_id, title):
    email = f"req-{uuid4().hex}@example.com"
    invite = client.post(
        f"/workspaces/{workspace_id}/invites",
        json={"email": email, "title": title},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text

    account = user_factory(email=email, name=f"{title} User")
    accepted = client.post(
        f"/invites/{invite.json()['token']}/accept",
        headers=account["headers"],
    )
    assert accepted.status_code == 200, accepted.text

    return account


def setup_workspace(client, user_factory, workspace_factory, quantity=10):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    product = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "name": "Farinha",
            "category": "Insumos",
            "quantity": quantity,
            "minimum_quantity": 2,
        },
        headers=owner["headers"],
    )
    assert product.status_code == 201, product.text

    seller = add_member(client, user_factory, owner["headers"], workspace["id"], "Vendedor")
    stocker = add_member(
        client, user_factory, owner["headers"], workspace["id"], "Estoquista"
    )

    return owner, workspace, product.json(), seller, stocker


def request_movement(client, workspace, product, account, **overrides):
    payload = {
        "product_id": product["id"],
        "movement_type": "saida",
        "quantity": 4,
        "reason": "Pedido do cliente #12",
        **overrides,
    }

    return client.post(
        f"/workspaces/{workspace['id']}/stock-requests",
        json=payload,
        headers=account["headers"],
    )


def product_quantity(client, workspace, product, headers):
    response = client.get(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()["quantity"]


def test_requester_asks_and_reviewer_approves(
    client, user_factory, workspace_factory
):
    owner, workspace, product, seller, stocker = setup_workspace(
        client, user_factory, workspace_factory
    )

    created = request_movement(client, workspace, product, seller)
    assert created.status_code == 201, created.text
    stock_request = created.json()
    assert stock_request["status"] == "pending"
    assert stock_request["requested_quantity"] == 4
    assert stock_request["requested_by_user_id"] == seller["user"]["id"]

    # Asking does not move stock.
    assert product_quantity(client, workspace, product, owner["headers"]) == 10

    approved = client.post(
        f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}/approve",
        json={},
        headers=stocker["headers"],
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "approved"
    assert body["approved_quantity"] == 4
    assert body["reviewed_by_user_id"] == stocker["user"]["id"]
    assert body["stock_movement_id"] is not None

    assert product_quantity(client, workspace, product, owner["headers"]) == 6

    movements = client.get(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock-movements",
        headers=owner["headers"],
    )
    assert movements.status_code == 200, movements.text
    movement = next(
        item for item in movements.json() if item["id"] == body["stock_movement_id"]
    )
    assert movement["movement_type"] == "saida"
    assert movement["quantity"] == 4
    assert movement["quantity_before"] == 10
    assert movement["quantity_after"] == 6
    assert movement["user_id"] == stocker["user"]["id"]
    assert f"Solicitação #{stock_request['id']}" in movement["reason"]

    logs = client.get(
        f"/workspaces/{workspace['id']}/audit-logs?limit=100",
        headers=owner["headers"],
    ).json()
    actions = {log["action"] for log in logs}
    assert {"stock_request.created", "stock_request.approved"} <= actions
    assert "stock.movement_created" in actions

    again = client.post(
        f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}/approve",
        json={},
        headers=owner["headers"],
    )
    assert again.status_code == 400, again.text
    assert product_quantity(client, workspace, product, owner["headers"]) == 6


def test_reviewer_changes_quantity_only_with_a_reason(
    client, user_factory, workspace_factory
):
    owner, workspace, product, seller, stocker = setup_workspace(
        client, user_factory, workspace_factory
    )
    stock_request = request_movement(
        client, workspace, product, seller, movement_type="entrada", quantity=10
    ).json()
    url = f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}/approve"

    no_reason = client.post(url, json={"quantity": 8}, headers=stocker["headers"])
    assert no_reason.status_code == 400, no_reason.text

    approved = client.post(
        url,
        json={"quantity": 8, "note": "Só chegaram 8 sacos"},
        headers=stocker["headers"],
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["requested_quantity"] == 10
    assert approved.json()["approved_quantity"] == 8
    assert approved.json()["review_note"] == "Só chegaram 8 sacos"
    assert product_quantity(client, workspace, product, owner["headers"]) == 18


def test_approval_keeps_stock_rules(client, user_factory, workspace_factory):
    owner, workspace, product, seller, stocker = setup_workspace(
        client, user_factory, workspace_factory, quantity=5
    )

    too_much = request_movement(client, workspace, product, seller, quantity=6)
    assert too_much.status_code == 400, too_much.text

    stock_request = request_movement(client, workspace, product, seller, quantity=5).json()

    # Stock drops before the review: the approval must not go negative.
    moved = client.post(
        f"/workspaces/{workspace['id']}/products/{product['id']}/stock",
        json={"movement_type": "saida", "quantity": 3, "reason": "Venda balcão"},
        headers=stocker["headers"],
    )
    assert moved.status_code == 201, moved.text

    approve_url = (
        f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}/approve"
    )
    denied = client.post(approve_url, json={}, headers=stocker["headers"])
    assert denied.status_code == 400, denied.text

    still_pending = client.get(
        f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}",
        headers=stocker["headers"],
    )
    assert still_pending.json()["status"] == "pending"
    assert product_quantity(client, workspace, product, owner["headers"]) == 2

    partial = client.post(
        approve_url,
        json={"quantity": 2, "note": "Só restavam 2"},
        headers=stocker["headers"],
    )
    assert partial.status_code == 200, partial.text
    assert product_quantity(client, workspace, product, owner["headers"]) == 0


def test_only_requesters_ask_and_only_operacao_up_reviews(
    client, user_factory, workspace_factory
):
    owner, workspace, product, seller, stocker = setup_workspace(
        client, user_factory, workspace_factory
    )
    viewer = add_member(
        client, user_factory, owner["headers"], workspace["id"], "Visualizador"
    )

    for account in (stocker, viewer, owner):
        denied = request_movement(client, workspace, product, account)
        assert denied.status_code == 403, denied.text

    adjust = request_movement(client, workspace, product, seller, movement_type="ajuste")
    assert adjust.status_code == 400, adjust.text

    stock_request = request_movement(client, workspace, product, seller).json()
    base = f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}"

    self_approve = client.post(f"{base}/approve", json={}, headers=seller["headers"])
    assert self_approve.status_code == 403, self_approve.text

    viewer_list = client.get(
        f"/workspaces/{workspace['id']}/stock-requests", headers=viewer["headers"]
    )
    assert viewer_list.status_code == 403, viewer_list.text

    reject_without_reason = client.post(
        f"{base}/reject", json={"note": "  "}, headers=stocker["headers"]
    )
    assert reject_without_reason.status_code == 422, reject_without_reason.text

    rejected = client.post(
        f"{base}/reject",
        json={"note": "Produto reservado para outra entrega"},
        headers=stocker["headers"],
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert product_quantity(client, workspace, product, owner["headers"]) == 10


def test_requesters_see_only_their_requests_and_can_cancel(
    client, user_factory, workspace_factory
):
    owner, workspace, product, seller, stocker = setup_workspace(
        client, user_factory, workspace_factory
    )
    buyer = add_member(client, user_factory, owner["headers"], workspace["id"], "Comprador")
    list_url = f"/workspaces/{workspace['id']}/stock-requests"

    mine = request_movement(client, workspace, product, seller).json()
    theirs = request_movement(
        client, workspace, product, buyer, movement_type="entrada"
    ).json()

    seller_list = client.get(list_url, headers=seller["headers"]).json()
    assert [item["id"] for item in seller_list] == [mine["id"]]

    stocker_list = client.get(list_url, headers=stocker["headers"]).json()
    assert {item["id"] for item in stocker_list} == {mine["id"], theirs["id"]}

    hidden = client.get(f"{list_url}/{theirs['id']}", headers=seller["headers"])
    assert hidden.status_code == 404, hidden.text

    cancel_other = client.post(
        f"{list_url}/{theirs['id']}/cancel", headers=seller["headers"]
    )
    assert cancel_other.status_code == 404, cancel_other.text

    reviewer_cancel = client.post(
        f"{list_url}/{mine['id']}/cancel", headers=stocker["headers"]
    )
    assert reviewer_cancel.status_code == 403, reviewer_cancel.text

    canceled = client.post(f"{list_url}/{mine['id']}/cancel", headers=seller["headers"])
    assert canceled.status_code == 200, canceled.text
    assert canceled.json()["status"] == "canceled"

    approve_canceled = client.post(
        f"{list_url}/{mine['id']}/approve", json={}, headers=stocker["headers"]
    )
    assert approve_canceled.status_code == 400, approve_canceled.text

    pending = client.get(list_url, headers=stocker["headers"]).json()
    assert [item["id"] for item in pending] == [theirs["id"]]

    closed = client.get(f"{list_url}?status=closed", headers=seller["headers"]).json()
    assert [item["id"] for item in closed] == [mine["id"]]

    bad_filter = client.get(f"{list_url}?status=whatever", headers=seller["headers"])
    assert bad_filter.status_code == 400, bad_filter.text


def test_conversation_between_requester_and_reviewers(
    client, user_factory, workspace_factory
):
    owner, workspace, product, seller, stocker = setup_workspace(
        client, user_factory, workspace_factory
    )
    buyer = add_member(client, user_factory, owner["headers"], workspace["id"], "Comprador")
    stock_request = request_movement(client, workspace, product, seller).json()
    url = f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}/messages"

    first = client.post(url, json={"body": "Pode separar hoje?"}, headers=seller["headers"])
    assert first.status_code == 201, first.text

    reply = client.post(
        url, json={"body": "Separo à tarde, ok?"}, headers=stocker["headers"]
    )
    assert reply.status_code == 201, reply.text

    outsider = client.post(url, json={"body": "Oi"}, headers=buyer["headers"])
    assert outsider.status_code == 404, outsider.text

    messages = client.get(url, headers=seller["headers"])
    assert messages.status_code == 200, messages.text
    assert [item["body"] for item in messages.json()] == [
        "Pode separar hoje?",
        "Separo à tarde, ok?",
    ]


def test_stock_requests_are_isolated_by_workspace(
    client, user_factory, workspace_factory
):
    owner, workspace, product, seller, stocker = setup_workspace(
        client, user_factory, workspace_factory
    )
    stock_request = request_movement(client, workspace, product, seller).json()

    other_owner = user_factory(name="Other")
    other_workspace = workspace_factory(other_owner["headers"], name="Outro")

    leaked = client.get(
        f"/workspaces/{other_workspace['id']}/stock-requests/{stock_request['id']}",
        headers=other_owner["headers"],
    )
    assert leaked.status_code == 404, leaked.text

    foreign = client.post(
        f"/workspaces/{workspace['id']}/stock-requests/{stock_request['id']}/approve",
        json={},
        headers=other_owner["headers"],
    )
    assert foreign.status_code == 403, foreign.text
