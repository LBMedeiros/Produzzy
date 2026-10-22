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
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/products",
    tags=["QR Code"],
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
