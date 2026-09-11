"""Concurrent stock withdrawals must never drive quantity negative.

This exercises the SELECT ... FOR UPDATE row lock in create_stock_movement
plus the CHECK (quantity >= 0) backstop: many threads race to withdraw from
the same product, and only as many as there is stock for may succeed.
"""

import threading

from app import crud, schemas
from app.database import SessionLocal
from app.errors import DomainError
from app.models import Product


def _make_product(client, headers, workspace_id, quantity):
    response = client.post(
        f"/workspaces/{workspace_id}/products",
        json={
            "name": "Produto concorrente",
            "category": "Insumos",
            "quantity": quantity,
            "minimum_quantity": 0,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_concurrent_withdrawals_never_go_negative(
    client, user_factory, workspace_factory
):
    owner = user_factory()
    workspace = workspace_factory(owner["headers"])
    workspace_id = workspace["id"]
    initial_quantity = 5
    thread_count = 15
    product = _make_product(client, owner["headers"], workspace_id, initial_quantity)

    barrier = threading.Barrier(thread_count)
    successes = []
    failures = []
    crashes = []
    lock = threading.Lock()

    def withdraw_one():
        # Release all threads into the critical section at the same instant to
        # maximize contention on the product row.
        barrier.wait()

        with SessionLocal() as db:
            try:
                crud.create_stock_movement(
                    workspace_id=workspace_id,
                    product_id=product["id"],
                    movement_data=schemas.StockMovementCreate(
                        movement_type="saida",
                        quantity=1,
                    ),
                    db=db,
                    user_id=owner["user"]["id"],
                )
            except DomainError:
                with lock:
                    failures.append(1)
            except Exception as unexpected:  # noqa: BLE001
                # e.g. IntegrityError from the CHECK constraint — the symptom of
                # a lost update if the row lock were not holding.
                with lock:
                    crashes.append(repr(unexpected))
            else:
                with lock:
                    successes.append(1)

    threads = [threading.Thread(target=withdraw_one) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # No thread hit a low-level DB error: the row lock produced clean,
    # serialized rejections rather than the CHECK constraint firing.
    assert crashes == []
    # Exactly the available units may be withdrawn; the rest are rejected.
    assert len(successes) == initial_quantity
    assert len(failures) == thread_count - initial_quantity

    with SessionLocal() as db:
        final_quantity = db.query(Product.quantity).filter(
            Product.id == product["id"]
        ).scalar()

    assert final_quantity == 0

    # One stock movement per successful withdrawal, and none pushed below zero.
    with SessionLocal() as db:
        movements = crud.list_product_stock_movements(
            product["id"], db, workspace_id, page=1, limit=100
        )
    assert len(movements) == initial_quantity
    assert all(movement.quantity_after >= 0 for movement in movements)
