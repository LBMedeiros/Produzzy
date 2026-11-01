"""Two admins saving the same category name at the same moment both pass the
name check; the unique index must turn the loser into a 400, not a 500."""
from app.crud import categories as categories_crud


def _skip_name_check(monkeypatch):
    # Simulates the race: the other request hasn't committed yet when this one
    # checks, so the check finds nothing.
    monkeypatch.setattr(categories_crud, "get_category_by_name", lambda *a, **k: None)


def test_concurrent_create_with_same_name_is_a_clean_400(
    client, user_factory, workspace_factory, monkeypatch
):
    owner = user_factory()
    workspace = workspace_factory(owner["headers"])
    url = f"/workspaces/{workspace['id']}/categories"

    first = client.post(url, json={"name": "Linhas"}, headers=owner["headers"])
    assert first.status_code == 201, first.text

    _skip_name_check(monkeypatch)
    second = client.post(url, json={"name": "Linhas"}, headers=owner["headers"])
    assert second.status_code == 400, second.text
    assert "Já existe uma categoria" in second.json()["detail"]


def test_concurrent_rename_to_same_name_is_a_clean_400(
    client, user_factory, workspace_factory, monkeypatch
):
    owner = user_factory()
    workspace = workspace_factory(owner["headers"])
    url = f"/workspaces/{workspace['id']}/categories"
    client.post(url, json={"name": "Linhas"}, headers=owner["headers"])
    other = client.post(url, json={"name": "Tecidos"}, headers=owner["headers"]).json()
    client.post(
        f"/workspaces/{workspace['id']}/products",
        json={"name": "Feltro", "category": "Tecidos", "quantity": 1, "minimum_quantity": 0},
        headers=owner["headers"],
    )

    _skip_name_check(monkeypatch)
    response = client.patch(
        f"{url}/{other['id']}", json={"name": "Linhas"}, headers=owner["headers"]
    )
    assert response.status_code == 400, response.text

    # Nothing half-applied: the product keeps its category name.
    products = client.get(
        f"/workspaces/{workspace['id']}/products", headers=owner["headers"]
    ).json()
    assert [p["category"] for p in products] == ["Tecidos"]
