from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, models
from app.dependencies import get_current_user, get_db
from app.services.qrcode_service import (
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
    products = crud.list_products(
        db=db,
        workspace_id=workspace_id,
        page=1,
        limit=100,
    )

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
    products = crud.list_products(
        db=db,
        workspace_id=workspace_id,
        page=1,
        limit=100,
    )

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
