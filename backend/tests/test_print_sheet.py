"""Print sheet for the redesigned Etiquetas page (docs/redesign Fase 5)."""
from io import BytesIO

from PIL import Image

from app.services.qrcode_service import PRINT_SHEET_MAX_LABELS


def create_product(client, workspace_id, headers, name):
    response = client.post(
        f"/workspaces/{workspace_id}/products",
        json={"category": "Etiquetas", "minimum_quantity": 1, "name": name, "quantity": 5},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def sheet_url(workspace_id):
    return f"/workspaces/{workspace_id}/products/print-sheet"


def png_pages(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    with Image.open(BytesIO(response.content)) as image:
        width, height = image.size
    # Pages are A4 (210 × 297) stacked vertically.
    return round(height / (width * 297 / 210))


def test_print_sheet_selected_products_copies_and_formats(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Print Owner")
    workspace = workspace_factory(owner["headers"], name="Print Workspace")
    first = create_product(client, workspace["id"], owner["headers"], "Primeiro")
    second = create_product(client, workspace["id"], owner["headers"], "Segundo")
    create_product(client, workspace["id"], owner["headers"], "Fora da seleção")

    response = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [first["id"], second["id"]], "copies": 2},
        headers=owner["headers"],
    )
    assert png_pages(response) == 1
    assert response.headers["x-sheet-pages"] == "1"

    # 3 columns × 4 rows of QR cards per A4 page: 2 products × 7 copies = 2 pages.
    response = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [first["id"], second["id"]], "copies": 7},
        headers=owner["headers"],
    )
    assert png_pages(response) == 2

    barcode = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [first["id"]], "code": "barcode"},
        headers=owner["headers"],
    )
    assert png_pages(barcode) == 1

    pdf = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [first["id"], second["id"]], "copies": 7, "format": "pdf"},
        headers=owner["headers"],
    )
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    # One PDF page per A4 sheet.
    assert pdf.content.count(b"/Type /Page") - pdf.content.count(b"/Type /Pages") == 2


def test_print_sheet_is_workspace_scoped_and_bounded(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Scope Owner")
    workspace = workspace_factory(owner["headers"], name="Scope Workspace")
    product = create_product(client, workspace["id"], owner["headers"], "Meu produto")
    outsider = user_factory(name="Scope Outsider")
    other_workspace = workspace_factory(outsider["headers"], name="Other Scope")
    other_product = create_product(
        client, other_workspace["id"], outsider["headers"], "Produto alheio"
    )

    # Another workspace's product id is simply not found here.
    foreign = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [other_product["id"]]},
        headers=owner["headers"],
    )
    assert foreign.status_code == 404

    # Non-members can't read the sheet at all.
    forbidden = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [product["id"]]},
        headers=outsider["headers"],
    )
    assert forbidden.status_code == 403

    # Viewers can print (read-only role).
    viewer = workspace_member_factory(owner["headers"], workspace["id"], "viewer")
    viewer_sheet = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [product["id"]]},
        headers=viewer["headers"],
    )
    assert png_pages(viewer_sheet) == 1

    within = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [product["id"]], "copies": 20},
        headers=owner["headers"],
    )
    assert within.status_code == 200, within.text

    many = [product["id"]] + [
        create_product(client, workspace["id"], owner["headers"], f"Lote {index}")["id"]
        for index in range(6)
    ]
    assert len(many) * 20 > PRINT_SHEET_MAX_LABELS
    too_many = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": many, "copies": 20},
        headers=owner["headers"],
    )
    assert too_many.status_code == 400
    assert "máximo" in too_many.json()["detail"]

    invalid = client.get(
        sheet_url(workspace["id"]),
        params={"product_ids": [product["id"]], "copies": 21},
        headers=owner["headers"],
    )
    assert invalid.status_code == 422
