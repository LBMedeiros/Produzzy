from io import BytesIO

from PIL import Image

from app.services.qrcode_service import get_product_barcode_value


def test_product_barcode_value_uses_nine_digits():
    assert get_product_barcode_value(1) == "000000001"
    assert get_product_barcode_value(25) == "000000025"
    assert get_product_barcode_value(123) == "000000123"


def test_qrcode_label_and_labels_sheet_routes(
    client,
    user_factory,
    workspace_factory,
):
    account = user_factory(name="Labels Owner")
    workspace = workspace_factory(account["headers"], name="Labels Workspace")
    product_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json={
            "category": "Identificação",
            "minimum_quantity": 1,
            "name": "Produto com etiqueta",
            "quantity": 5,
        },
        headers=account["headers"],
    )

    assert product_response.status_code == 201, product_response.text
    product = product_response.json()

    image_paths = [
        f"/workspaces/{workspace['id']}/products/{product['id']}/qrcode",
        f"/workspaces/{workspace['id']}/products/{product['id']}/barcode",
        f"/workspaces/{workspace['id']}/products/{product['id']}/label",
        f"/workspaces/{workspace['id']}/products/labels-sheet",
    ]

    for path in image_paths:
        response = client.get(path, headers=account["headers"])

        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/png"
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")

        with Image.open(BytesIO(response.content)) as image:
            assert image.width > 0
            assert image.height > 0

    label_response = client.get(
        f"/workspaces/{workspace['id']}/products/{product['id']}/label",
        headers=account["headers"],
    )

    with Image.open(BytesIO(label_response.content)) as label:
        assert label.size == (595, 357)
