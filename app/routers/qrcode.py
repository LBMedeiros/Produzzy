from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud
from app.dependencies import get_db
from app.services.qrcode_service import generate_qrcode_image


router = APIRouter(
    prefix="/products",
    tags=["QR Code"],
)


@router.get("/{product_id}/qrcode")
def generate_product_qrcode(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    product = crud.get_product_by_id(product_id, db)

    product_url = str(
        request.url_for(
            "get_product",
            product_id=product.id,
        )
    )

    qr_image = generate_qrcode_image(product_url)

    filename = f"product-{product.id}-qrcode.png"

    return StreamingResponse(
        qr_image,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )