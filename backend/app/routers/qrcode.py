from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, models
from app.dependencies import get_current_user, get_db
from app.services.qrcode_service import (
    PRINT_SHEET_MAX_LABELS,
    generate_print_sheet_pages,
    pages_to_pdf_buffer,
    pages_to_png_buffer,
    generate_product_barcode_image,
    generate_product_label_image,
    generate_product_qrcode_image,
    generate_products_labels_sheet_image,
    generate_products_qrcodes_sheet_image,
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/products",
    tags=["QR Code"],
)


@router.get("/labels-sheet")
def generate_products_labels_sheet(
    workspace_id: int,
    request: Request,
    label_width_mm: int = Query(default=70, ge=40, le=100),
    label_height_mm: int = Query(default=42, ge=35, le=140),
    qr_size_mm: int | None = Query(default=None, ge=18, le=80),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )
    products = crud.list_active_products_for_export(db, workspace_id)

    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum produto cadastrado para gerar etiquetas.",
        )

    labels_data = []

    for product in products:
        product_url = str(
            request.url_for(
                "get_workspace_product",
                workspace_id=workspace_id,
                product_id=product.id,
            )
        )

        labels_data.append(
            {
                "data": product_url,
                "product_name": product.name,
                "product_category": product.category,
                "product_id": product.id,
            }
        )

    sheet_image = generate_products_labels_sheet_image(
        labels_data=labels_data,
        label_width_mm=label_width_mm,
        label_height_mm=label_height_mm,
        qr_size_mm=qr_size_mm,
    )

    return StreamingResponse(
        sheet_image,
        media_type="image/png",
        headers={
            "Content-Disposition": 'inline; filename="products-labels-sheet-a4.png"'
        },
    )


@router.get("/qrcodes-sheet")
def generate_products_qrcodes_sheet(
    workspace_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )
    products = crud.list_active_products_for_export(db, workspace_id)

    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum produto cadastrado para gerar QR Codes.",
        )

    qrcodes_data = []

    for product in products:
        product_url = str(
            request.url_for(
                "get_workspace_product",
                workspace_id=workspace_id,
                product_id=product.id,
            )
        )
        qrcodes_data.append(
            {
                "data": product_url,
                "product_name": product.name,
                "product_id": product.id,
            }
        )

    sheet_image = generate_products_qrcodes_sheet_image(qrcodes_data)

    return StreamingResponse(
        sheet_image,
        media_type="image/png",
        headers={
            "Content-Disposition": 'inline; filename="products-qrcodes-print.png"'
        },
    )


@router.get("/print-sheet")
def generate_products_print_sheet(
    workspace_id: int,
    request: Request,
    product_ids: list[int] | None = Query(default=None),
    copies: int = Query(default=1, ge=1, le=20),
    output_format: Literal["png", "pdf"] = Query(default="png", alias="format"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """A4 sheet (3 columns) for the selected products — one label each with
    the QR Code (brand icon in the centre) and the barcode, N copies each — as
    a PNG preview or a PDF."""
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )
    products = crud.list_active_products_for_export(db, workspace_id)

    if product_ids:
        # Only active products of this workspace; keep the selection order.
        by_id = {product.id: product for product in products}
        products = [by_id[pid] for pid in dict.fromkeys(product_ids) if pid in by_id]

    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum produto selecionado para imprimir.",
        )

    if len(products) * copies > PRINT_SHEET_MAX_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Muitas etiquetas de uma vez (máximo {PRINT_SHEET_MAX_LABELS}). "
                "Selecione menos produtos ou cópias."
            ),
        )

    items = []

    for product in products:
        item = {
            "data": str(
                request.url_for(
                    "get_workspace_product",
                    workspace_id=workspace_id,
                    product_id=product.id,
                )
            ),
            "product_category": product.category,
            "product_id": product.id,
            "product_name": product.name,
        }
        items.extend([item] * copies)

    pages = generate_print_sheet_pages(items)

    if output_format == "pdf":
        return StreamingResponse(
            pages_to_pdf_buffer(pages),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="etiquetas-produzzy.pdf"'},
        )

    return StreamingResponse(
        pages_to_png_buffer(pages),
        media_type="image/png",
        headers={
            "Content-Disposition": 'inline; filename="etiquetas-produzzy.png"',
            "X-Sheet-Pages": str(len(pages)),
            "Access-Control-Expose-Headers": "X-Sheet-Pages",
        },
    )


@router.get("/{product_id}/barcode")
def generate_product_barcode(
    workspace_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )
    product = crud.get_product_by_id(product_id, db, workspace_id)
    barcode_image = generate_product_barcode_image(product)
    filename = f"product-{product.id}-barcode.png"

    return StreamingResponse(
        barcode_image,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )


@router.get("/{product_id}/qrcode")
def generate_product_qrcode(
    workspace_id: int,
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )
    product = crud.get_product_by_id(product_id, db, workspace_id)

    product_url = str(
        request.url_for(
            "get_workspace_product",
            workspace_id=workspace_id,
            product_id=product.id,
        )
    )

    qr_image = generate_product_qrcode_image(
        data=product_url,
        product_name=product.name,
    )

    filename = f"product-{product.id}-qrcode.png"

    return StreamingResponse(
        qr_image,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )


@router.get("/{product_id}/label")
def generate_product_label(
    workspace_id: int,
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )
    product = crud.get_product_by_id(product_id, db, workspace_id)

    product_url = str(
        request.url_for(
            "get_workspace_product",
            workspace_id=workspace_id,
            product_id=product.id,
        )
    )

    label_image = generate_product_label_image(
        data=product_url,
        product_name=product.name,
        product_category=product.category,
        product_id=product.id,
    )

    filename = f"product-{product.id}-label.png"

    return StreamingResponse(
        label_image,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )
