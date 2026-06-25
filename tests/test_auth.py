def test_register_login_and_me(client, user_factory):
    account = user_factory(name="Auth User")

    response = client.get("/auth/me", headers=account["headers"])

    assert response.status_code == 200
    assert response.json()["email"] == account["email"]
