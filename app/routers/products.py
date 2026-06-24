from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app import crud, schemas, models


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=schemas.ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: schemas.ProductCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_product(product_data, db)


@router.get("", response_model=list[schemas.ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    return crud.list_products(
        db=db,
        category=category,
        search=search,
    )


@router.get("/low-stock", response_model=list[schemas.ProductResponse])
def list_low_stock_products(db: Session = Depends(get_db)):
    return crud.list_low_stock_products(db)


@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    return crud.get_product_by_id(product_id, db)


@router.patch("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.update_product(product_id, product_data, db)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.delete_product(product_id, db)

    return None


@router.post(
    "/{product_id}/stock",
    response_model=schemas.StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    product_id: int,
    movement_data: schemas.StockMovementCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_stock_movement(product_id, movement_data, db)


@router.get(
    "/{product_id}/stock-movements",
    response_model=list[schemas.StockMovementResponse],
)
def list_product_stock_movements(
    product_id: int,
    db: Session = Depends(get_db),
):
    return crud.list_product_stock_movements(product_id, db)
