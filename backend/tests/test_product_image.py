"""Product photos: upload, replace, remove, permissions and storage cleanup."""
from io import BytesIO

import pytest
from PIL import Image

from app.services import product_image_service


def png_bytes(size=(64, 48)):
    buffer = BytesIO()
    Image.new("RGB", size, "#2453c6").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture()
def storage(monkeypatch):
    """Fake Cloudinary: records uploads and deletions."""
    state = {"uploads": [], "deleted": []}

    def upload(content, workspace_id, product_id):
        public_id = f"products/ws{workspace_id}_p{product_id}_{len(state['uploads'])}"
        state["uploads"].append((public_id, content))
        return product_image_service.ProductImageUploadResult(
            url=f"https://res.cloudinary.com/demo/image/upload/{public_id}.webp",
            public_id=public_id,
        )

    monkeypatch.setattr(product_image_service, "upload_product_image", upload)
    monkeypatch.setattr(
        product_image_service,
        "delete_product_image",
        lambda public_id: state["deleted"].append(public_id) if public_id else None,
    )
    return state


def create_product(client, headers, workspace_id, name="Linha azul"):
    response = client.post(
        f"/workspaces/{workspace_id}/products",
        json={"name": name, "category": "Linhas", "quantity": 5, "minimum_quantity": 10},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, headers, workspace_id, product_id, content=None, filename="foto.png"):
    return client.post(
        f"/workspaces/{workspace_id}/products/{product_id}/image",
        files={"file": (filename, content if content is not None else png_bytes(), "image/png")},
        headers=headers,
    )


def test_upload_replace_and_remove_product_image(
    client, user_factory, workspace_factory, storage
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    product = create_product(client, owner["headers"], workspace["id"])
    assert product["image_url"] is None

    first = upload(client, owner["headers"], workspace["id"], product["id"])
    assert first.status_code == 200, first.text
    first_url = first.json()["image_url"]
    assert first_url.endswith(".webp")
    # Stored as WebP regardless of the uploaded format.
    with Image.open(BytesIO(storage["uploads"][0][1])) as stored:
        assert stored.format == "WEBP"

    listed = client.get(f"/workspaces/{workspace['id']}/products", headers=owner["headers"])
    assert [item["image_url"] for item in listed.json()] == [first_url]

    second = upload(client, owner["headers"], workspace["id"], product["id"])
    assert second.status_code == 200, second.text
    assert second.json()["image_url"] != first_url
    # The replaced photo is removed from storage.
    assert storage["deleted"] == [storage["uploads"][0][0]]

    removed = client.delete(
        f"/workspaces/{workspace['id']}/products/{product['id']}/image",
        headers=owner["headers"],
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["image_url"] is None
    assert storage["deleted"][-1] == storage["uploads"][1][0]
    assert "image_public_id" not in removed.json()


def test_only_owner_and_admin_change_product_images(
    client, user_factory, workspace_factory, workspace_member_factory, storage
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    product = create_product(client, owner["headers"], workspace["id"])
    admin = workspace_member_factory(owner["headers"], workspace["id"], "admin")
    employee = workspace_member_factory(owner["headers"], workspace["id"], "employee")
    viewer = workspace_member_factory(owner["headers"], workspace["id"], "viewer")

    assert upload(client, admin["headers"], workspace["id"], product["id"]).status_code == 200
    for member in (employee, viewer):
        assert upload(client, member["headers"], workspace["id"], product["id"]).status_code == 403
        assert (
            client.delete(
                f"/workspaces/{workspace['id']}/products/{product['id']}/image",
                headers=member["headers"],
            ).status_code
            == 403
        )
    assert len(storage["uploads"]) == 1


def test_product_image_is_workspace_scoped(client, user_factory, workspace_factory, storage):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    product = create_product(client, owner["headers"], workspace["id"])
    other = user_factory(name="Other")
    other_workspace = workspace_factory(other["headers"], name="Other")

    # The other owner can't reach this product through their own workspace.
    response = upload(client, other["headers"], other_workspace["id"], product["id"])
    assert response.status_code == 404, response.text
    assert storage["uploads"] == []


def test_product_image_rejects_non_images(client, user_factory, workspace_factory, storage):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    product = create_product(client, owner["headers"], workspace["id"])

    response = upload(
        client, owner["headers"], workspace["id"], product["id"], content=b"not an image", filename="x.txt"
    )
    assert response.status_code == 400, response.text
    assert storage["uploads"] == []


def test_deleting_workspace_removes_its_product_images(
    client, user_factory, workspace_factory, storage
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    first = create_product(client, owner["headers"], workspace["id"], name="A")
    second = create_product(client, owner["headers"], workspace["id"], name="B")
    create_product(client, owner["headers"], workspace["id"], name="Sem foto")
    upload(client, owner["headers"], workspace["id"], first["id"])
    upload(client, owner["headers"], workspace["id"], second["id"])

    response = client.delete(f"/workspaces/{workspace['id']}", headers=owner["headers"])
    assert response.status_code in (200, 204), response.text
    assert sorted(storage["deleted"]) == sorted(public_id for public_id, _ in storage["uploads"])


def test_deleting_account_removes_photos_of_its_solo_workspaces(
    client, user_factory, workspace_factory, storage
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    product = create_product(client, owner["headers"], workspace["id"])
    upload(client, owner["headers"], workspace["id"], product["id"])

    response = client.request(
        "DELETE",
        "/auth/me",
        json={"current_password": owner["password"]},
        headers=owner["headers"],
    )
    assert response.status_code == 200, response.text
    assert storage["deleted"] == [storage["uploads"][0][0]]
