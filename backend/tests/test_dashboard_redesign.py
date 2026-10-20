"""Dashboard data for the redesigned Início (docs/redesign Fase 2)."""
from datetime import datetime, timedelta, timezone

from app import models
from app.database import SessionLocal


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


def move_stock(client, workspace_id, headers, product_id, movement_type, quantity):
    response = client.post(
        f"/workspaces/{workspace_id}/products/{product_id}/stock",
        json={"movement_type": movement_type, "quantity": quantity},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    return response.json()


def create_replenishment(client, workspace_id, headers, product_id, quantity=5):
    response = client.post(
        f"/workspaces/{workspace_id}/replenishments",
        json={"product_id": product_id, "type": "purchase", "quantity_needed": quantity},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    return response.json()


def set_replenishment_status(client, workspace_id, headers, request_id, status):
    response = client.patch(
        f"/workspaces/{workspace_id}/replenishments/{request_id}",
        json={"status": status},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()


def get_dashboard(client, workspace_id, headers, **params):
    response = client.get(
        f"/workspaces/{workspace_id}/dashboard",
        params=params,
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()


def test_dashboard_movements_by_day_counts_directions_and_isolates_workspaces(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Chart Owner")
    workspace = workspace_factory(owner["headers"], name="Chart Workspace")
    other = user_factory(name="Chart Other")
    other_workspace = workspace_factory(other["headers"], name="Other Chart")

    product = create_product(client, workspace["id"], owner["headers"], "Luva", 10)
    move_stock(client, workspace["id"], owner["headers"], product["id"], "entrada", 5)
    move_stock(client, workspace["id"], owner["headers"], product["id"], "saida", 3)
    # Adjusting down counts as an exit; adjusting to the same value is neither.
    move_stock(client, workspace["id"], owner["headers"], product["id"], "ajuste", 2)
    move_stock(client, workspace["id"], owner["headers"], product["id"], "ajuste", 2)

    other_product = create_product(
        client, other_workspace["id"], other["headers"], "Outro", 10
    )
    move_stock(
        client, other_workspace["id"], other["headers"], other_product["id"], "entrada", 1
    )

    data = get_dashboard(
        client, workspace["id"], owner["headers"], tz="America/Sao_Paulo"
    )
    days = data["movements_by_day"]

    assert len(days) == 7
    dates = [day["date"] for day in days]
    assert dates == sorted(dates)
    today = days[-1]
    # Product creation with initial stock doesn't create a movement row.
    assert today["total"] == 4
    assert today["entries"] == 1
    assert today["exits"] == 2
    assert sum(day["total"] for day in days[:-1]) == 0
    assert data["summary"]["movements_today"] == 4
    assert data["summary"]["movements_yesterday"] == 0


def test_dashboard_lists_stalled_and_ready_replenishments(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Board Owner")
    workspace = workspace_factory(owner["headers"], name="Board Workspace")
    other = user_factory(name="Board Other")
    other_workspace = workspace_factory(other["headers"], name="Other Board")

    stalled_product = create_product(
        client, workspace["id"], owner["headers"], "Toner", 1
    )
    recent_product = create_product(
        client, workspace["id"], owner["headers"], "Parafuso", 1
    )
    ready_product = create_product(client, workspace["id"], owner["headers"], "Fita", 1)
    other_product = create_product(
        client, other_workspace["id"], other["headers"], "Outro", 1
    )

    stalled = create_replenishment(
        client, workspace["id"], owner["headers"], stalled_product["id"]
    )
    set_replenishment_status(
        client, workspace["id"], owner["headers"], stalled["id"], "in_progress"
    )
    recent = create_replenishment(
        client, workspace["id"], owner["headers"], recent_product["id"]
    )
    set_replenishment_status(
        client, workspace["id"], owner["headers"], recent["id"], "in_progress"
    )
    ready = create_replenishment(
        client, workspace["id"], owner["headers"], ready_product["id"]
    )
    set_replenishment_status(
        client, workspace["id"], owner["headers"], ready["id"], "in_progress"
    )
    set_replenishment_status(
        client, workspace["id"], owner["headers"], ready["id"], "completed"
    )
    other_request = create_replenishment(
        client, other_workspace["id"], other["headers"], other_product["id"]
    )
    set_replenishment_status(
        client, other_workspace["id"], other["headers"], other_request["id"], "in_progress"
    )

    four_days_ago = datetime.now(timezone.utc) - timedelta(days=4)
    with SessionLocal() as db:
        for request_id in (stalled["id"], other_request["id"]):
            db.query(models.ReplenishmentRequest).filter(
                models.ReplenishmentRequest.id == request_id
            ).update(
                {models.ReplenishmentRequest.updated_at: four_days_ago},
                synchronize_session=False,
            )
        db.commit()

    data = get_dashboard(client, workspace["id"], owner["headers"])

    assert [item["id"] for item in data["stalled_replenishments"]] == [stalled["id"]]
    assert data["stalled_replenishments"][0]["product_name"] == "Toner"
    assert [item["id"] for item in data["ready_replenishments"]] == [ready["id"]]
    assert data["ready_replenishments"][0]["status"] == "completed"


def test_dashboard_attention_and_summary_know_active_replenishments(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Attention Owner")
    workspace = workspace_factory(owner["headers"], name="Attention Workspace")

    zero_with = create_product(client, workspace["id"], owner["headers"], "Zero A", 0)
    create_product(client, workspace["id"], owner["headers"], "Zero B", 0)
    low_with = create_product(client, workspace["id"], owner["headers"], "Low A", 2)
    create_product(client, workspace["id"], owner["headers"], "Low B", 3)
    create_product(client, workspace["id"], owner["headers"], "Healthy", 50)

    zero_request = create_replenishment(
        client, workspace["id"], owner["headers"], zero_with["id"]
    )
    create_replenishment(client, workspace["id"], owner["headers"], low_with["id"])

    data = get_dashboard(client, workspace["id"], owner["headers"])
    summary = data["summary"]

    assert summary["out_of_stock_products"] == 2
    assert summary["low_stock_products"] == 2
    assert summary["out_of_stock_without_replenishment"] == 1
    assert summary["low_stock_in_replenishment"] == 1

    by_name = {item["name"]: item for item in data["attention_products"]}
    assert by_name["Zero A"]["active_replenishment_id"] == zero_request["id"]
    assert by_name["Zero A"]["active_replenishment_status"] == "open"
    assert by_name["Zero B"]["active_replenishment_id"] is None
    assert by_name["Low A"]["active_replenishment_id"] is not None
    assert "Healthy" not in by_name


def test_dashboard_activity_has_readable_names_and_stays_admin_only(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Ana Owner")
    workspace = workspace_factory(owner["headers"], name="Activity Workspace")
    product = create_product(client, workspace["id"], owner["headers"], "Café", 10)
    move_stock(client, workspace["id"], owner["headers"], product["id"], "entrada", 20)

    data = get_dashboard(client, workspace["id"], owner["headers"], tz="Not/AZone")

    movement_log = next(
        item
        for item in data["recent_activity"]
        if item["action"] == "stock.movement_created"
    )
    assert movement_log["user_name"] == "Ana Owner"
    assert movement_log["product_name"] == "Café"
    assert movement_log["metadata"]["quantity"] == 20
    product_log = next(
        item for item in data["recent_activity"] if item["action"] == "product.created"
    )
    assert product_log["product_name"] == "Café"
    # An unknown timezone falls back instead of failing.
    assert len(data["movements_by_day"]) == 7

    employee = workspace_member_factory(owner["headers"], workspace["id"], "employee")
    employee_data = get_dashboard(client, workspace["id"], employee["headers"])
    assert employee_data["recent_activity"] == []
    assert len(employee_data["movements_by_day"]) == 7
