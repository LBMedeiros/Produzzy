
from PIL import Image, ImageChops, ImageDraw

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


def test_qrcode_keeps_the_produzzy_logo_in_the_center():
    # The logo must stay in printed QR Codes, with high error correction so
    # the covered modules don't break scanning.
    with_logo = generate_qrcode_pil("https://example.com/p/1")
    plain = generate_qrcode_pil("https://example.com/p/1", include_brand_icon=False)

    assert with_logo.size == plain.size
    box = ImageChops.difference(with_logo, plain).getbbox()
    assert box is not None
    center_x, center_y = with_logo.width // 2, with_logo.height // 2
    assert box[0] < center_x < box[2]
    assert box[1] < center_y < box[3]
    # Only the middle changes; the finder patterns in the corners stay intact.
    assert box[2] - box[0] < with_logo.width * 0.3


def test_print_sheet_skips_products_in_the_trash(
    client,
    user_factory,
    workspace_factory,
):
    account = user_factory(name="Active Sheets Owner")
    workspace = workspace_factory(account["headers"], name="Active Sheets")
    create_product(client, workspace["id"], account["headers"], name="Produto ativo")
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

    only_deleted = client.get(
        f"/workspaces/{workspace['id']}/products/print-sheet",
        params={"product_ids": [deleted_product["id"]]},
        headers=account["headers"],
    )
    assert only_deleted.status_code == 404, only_deleted.text

    everything = client.get(
        f"/workspaces/{workspace['id']}/products/print-sheet",
        headers=account["headers"],
    )
    assert everything.status_code == 200, everything.text
    assert everything.headers["X-Sheet-Pages"] == "1"
