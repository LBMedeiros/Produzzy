from datetime import datetime, timezone

from jose import jwt

from app.services import rate_limit_service
from app.services.security_service import (
    ALGORITHM,
    SECRET_KEY,
    create_password_reset_token,
)


def token_lifetime_seconds(token: str) -> float:
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)

    return (expires_at - datetime.now(timezone.utc)).total_seconds()


def login(client, account, remember_me=None):
    body = {"email": account["email"], "password": account["password"]}

    if remember_me is not None:
        body["remember_me"] = remember_me

    response = client.post("/auth/login", json=body)
    assert response.status_code == 200, response.text

    return response.json()["access_token"]


def bearer(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_remember_me_issues_a_long_session_and_default_stays_short(
    client,
    user_factory,
):
    account = user_factory()

    short_token = login(client, account)
    long_token = login(client, account, remember_me=True)

    assert token_lifetime_seconds(short_token) <= 60 * 60 + 5
    assert token_lifetime_seconds(long_token) > 29 * 24 * 60 * 60
    assert client.get("/auth/me", headers=bearer(long_token)).status_code == 200


def test_oauth_form_login_accepts_remember_me(client, user_factory):
    account = user_factory()

    response = client.post(
        "/auth/token",
        data={
            "username": account["email"],
            "password": account["password"],
            "remember_me": "true",
        },
    )

    assert response.status_code == 200, response.text
    assert token_lifetime_seconds(response.json()["access_token"]) > 29 * 24 * 3600


def test_password_change_ends_other_sessions_and_keeps_the_current_one(
    client,
    user_factory,
):
    account = user_factory()
    other_device_token = login(client, account)
    current_token = login(client, account, remember_me=True)

    response = client.post(
        "/auth/me/change-password",
        json={
            "current_password": account["password"],
            "new_password": "Another-password2@",
        },
        headers=bearer(current_token),
    )

    assert response.status_code == 200, response.text
    new_token = response.json()["access_token"]

    # The fresh token works and keeps the "remember me" lifetime.
    assert client.get("/auth/me", headers=bearer(new_token)).status_code == 200
    assert token_lifetime_seconds(new_token) > 29 * 24 * 3600

    # Sessions issued before the change no longer work.
    assert client.get("/auth/me", headers=bearer(other_device_token)).status_code == 401
    assert client.get("/auth/me", headers=bearer(current_token)).status_code == 401


def test_password_reset_link_token_is_not_a_session(client, user_factory):
    account = user_factory()
    reset_token = create_password_reset_token(account["email"], "anything")

    response = client.get("/auth/me", headers=bearer(reset_token))

    assert response.status_code == 401


def test_product_list_includes_each_products_latest_movement(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Last Movement Owner")
    workspace = workspace_factory(owner["headers"])
    base_url = f"/workspaces/{workspace['id']}/products"

    moved = client.post(
        base_url,
        json={"name": "Movido", "category": "Geral", "quantity": 10, "minimum_quantity": 1},
        headers=owner["headers"],
    ).json()
    untouched = client.post(
        base_url,
        json={"name": "Parado", "category": "Geral", "quantity": 1, "minimum_quantity": 5},
        headers=owner["headers"],
    ).json()

    for movement_type, quantity in [("entrada", 5), ("saida", 3)]:
        response = client.post(
            f"{base_url}/{moved['id']}/stock",
            json={"movement_type": movement_type, "quantity": quantity},
            headers=owner["headers"],
        )
        assert response.status_code in (200, 201), response.text

    products = {
        product["id"]: product
        for product in client.get(base_url, headers=owner["headers"]).json()
    }

    last_movement = products[moved["id"]]["last_movement"]
    assert last_movement["movement_type"] == "saida"
    assert last_movement["quantity"] == 3
    assert last_movement["user_name"] == "Last Movement Owner"
    assert products[untouched["id"]]["last_movement"] is None

    low_stock = client.get(f"{base_url}/low-stock", headers=owner["headers"]).json()
    assert [product["id"] for product in low_stock] == [untouched["id"]]
    assert low_stock[0]["last_movement"] is None


class FakeRequest:
    def __init__(self, forwarded_for=None, host="10.0.0.1"):
        self.headers = {"x-forwarded-for": forwarded_for} if forwarded_for else {}
        self.client = type("Client", (), {"host": host})()


def test_rate_limit_key_uses_the_proxy_appended_client_ip():
    key_for = rate_limit_service.build_rate_limit_key

    # Behind the proxy, two users get different buckets for the same scope.
    assert key_for(FakeRequest("203.0.113.5"), "google") != key_for(
        FakeRequest("198.51.100.7"), "google"
    )
    # Only the last (proxy-appended) entry counts, so a client can't dodge the
    # limit by sending its own X-Forwarded-For.
    assert key_for(FakeRequest("1.1.1.1, 203.0.113.5"), "google") == key_for(
        FakeRequest("9.9.9.9, 203.0.113.5"), "google"
    )
    # Without the header it falls back to the socket address.
    assert key_for(FakeRequest(host="10.0.0.9"), "x") != key_for(
        FakeRequest(host="10.0.0.8"), "x"
    )
