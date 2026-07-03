from io import BytesIO

from PIL import Image, ImageChops, ImageDraw

from app.routers import qrcode as qrcode_router
from app.services.qrcode_service import (
    generate_qrcode_pil,
    get_product_barcode_value,
    load_font,
    text_size,
    wrap_text_without_truncation,
)


def create_product(client, workspace_id, headers, name="Produto com etiqueta"):
    response = client.post(
        f"/workspaces/{workspace_id}/products",
        json={
            "category": "Identificação",
            "minimum_quantity": 1,
            "name": name,
            "quantity": 5,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def assert_png_response(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")

    with Image.open(BytesIO(response.content)) as image:
        assert image.width > 0
        assert image.height > 0


def tiny_png_buffer():
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_product_barcode_value_uses_nine_digits():
    assert get_product_barcode_value(1) == "000000001"
    assert get_product_barcode_value(25) == "000000025"
    assert get_product_barcode_value(123) == "000000123"


def test_product_name_wrap_preserves_the_complete_text():
    product_name = (
        "Produto artesanal com um nome muito longo para identificação "
        "durante a impressão e o recorte"
    )
    image = Image.new("RGB", (320, 120), "white")
    draw = ImageDraw.Draw(image)
    font = load_font(24, bold=True)
    lines = wrap_text_without_truncation(
        draw,
        product_name,
        font,
        max_width=280,
    )

    assert " ".join(lines) == product_name
    assert all(text_size(draw, line, font)[0] <= 280 for line in lines)


def test_qrcode_label_and_labels_sheet_routes(
    client,
    user_factory,
    workspace_factory,
):
    account = user_factory(name="Labels Owner")
    workspace = workspace_factory(account["headers"], name="Labels Workspace")
    product = create_product(
        client,
        workspace["id"],
        account["headers"],
    )

    image_paths = [
        f"/workspaces/{workspace['id']}/products/{product['id']}/qrcode",
        f"/workspaces/{workspace['id']}/products/{product['id']}/barcode",
        f"/workspaces/{workspace['id']}/products/{product['id']}/label",
        f"/workspaces/{workspace['id']}/products/labels-sheet",
        f"/workspaces/{workspace['id']}/products/qrcodes-sheet",
    ]

    for path in image_paths:
        response = client.get(path, headers=account["headers"])
        assert_png_response(response)

    label_response = client.get(
        f"/workspaces/{workspace['id']}/products/{product['id']}/label",
        headers=account["headers"],
    )

    with Image.open(BytesIO(label_response.content)) as label:
        assert label.size == (595, 357)


def test_individual_qrcode_has_product_name_above_scannable_area(
    client,
    user_factory,
    workspace_factory,
):
    account = user_factory(name="Named QR Owner")
    workspace = workspace_factory(account["headers"], name="Named QR Workspace")
    product = create_product(
        client,
        workspace["id"],
        account["headers"],
        name=(
            "Produto artesanal com um nome longo para identificação "
            "durante a impressão"
        ),
    )
    response = client.get(
        f"/workspaces/{workspace['id']}/products/{product['id']}/qrcode",
        headers=account["headers"],
    )
    assert_png_response(response)

    product_url = (
        f"http://testserver/workspaces/{workspace['id']}/products/{product['id']}"
    )
    raw_qrcode = generate_qrcode_pil(product_url)

    with Image.open(BytesIO(response.content)).convert("RGB") as image:
        horizontal_padding = (image.width - raw_qrcode.width) // 2
        qrcode_top = image.height - raw_qrcode.height - horizontal_padding
        name_area = image.crop((0, 0, image.width, qrcode_top))
        white_area = Image.new("RGB", name_area.size, "white")

        assert image.height > raw_qrcode.height
        assert qrcode_top > 0
        assert ImageChops.difference(name_area, white_area).getbbox() is not None


def test_print_sheets_only_receive_active_products(
    client,
    user_factory,
    workspace_factory,
    monkeypatch,
):
    account = user_factory(name="Active Sheets Owner")
    workspace = workspace_factory(account["headers"], name="Active Sheets")
    active_product = create_product(
        client,
        workspace["id"],
        account["headers"],
        name="Produto ativo",
    )
    deleted_product = create_product(
        client,
        workspace["id"],
        account["headers"],
        name="Produto na lixeira",
    )
    delete_response = client.delete(
        f"/workspaces/{workspace['id']}/products/{deleted_product['id']}",
        headers=account["headers"],
    )
    assert delete_response.status_code == 200, delete_response.text
    received_products = {}

    def capture_labels(labels_data, **_kwargs):
        received_products["labels"] = labels_data
        return tiny_png_buffer()

    def capture_qrcodes(qrcodes_data, **_kwargs):
        received_products["qrcodes"] = qrcodes_data
        return tiny_png_buffer()

    monkeypatch.setattr(
        qrcode_router,
        "generate_products_labels_sheet_image",
        capture_labels,
    )
    monkeypatch.setattr(
        qrcode_router,
        "generate_products_qrcodes_sheet_image",
        capture_qrcodes,
    )

    labels_response = client.get(
        f"/workspaces/{workspace['id']}/products/labels-sheet",
        headers=account["headers"],
    )
    qrcodes_response = client.get(
        f"/workspaces/{workspace['id']}/products/qrcodes-sheet",
        headers=account["headers"],
    )
    assert_png_response(labels_response)
    assert_png_response(qrcodes_response)

    assert [item["product_id"] for item in received_products["labels"]] == [
        active_product["id"]
    ]
    assert [item["product_id"] for item in received_products["qrcodes"]] == [
        active_product["id"]
    ]


def test_qrcode_routes_enforce_workspace_membership_and_product_scope(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Scoped QR Owner")
    owner_workspace = workspace_factory(
        owner["headers"],
        name="Scoped QR Workspace",
    )
    owner_product = create_product(
        client,
        owner_workspace["id"],
        owner["headers"],
    )
    other_owner = user_factory(name="Other QR Owner")
    other_workspace = workspace_factory(
        other_owner["headers"],
        name="Other QR Workspace",
    )

    cross_workspace_response = client.get(
        (
            f"/workspaces/{other_workspace['id']}/products/"
            f"{owner_product['id']}/qrcode"
        ),
        headers=other_owner["headers"],
    )
    assert cross_workspace_response.status_code == 404

    protected_paths = [
        f"/workspaces/{owner_workspace['id']}/products/{owner_product['id']}/qrcode",
        f"/workspaces/{owner_workspace['id']}/products/{owner_product['id']}/label",
        f"/workspaces/{owner_workspace['id']}/products/labels-sheet",
        f"/workspaces/{owner_workspace['id']}/products/qrcodes-sheet",
    ]

    for path in protected_paths:
        response = client.get(path, headers=other_owner["headers"])
        assert response.status_code == 403, response.text
