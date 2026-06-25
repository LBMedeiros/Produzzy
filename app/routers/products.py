from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app import crud, schemas, models


router = APIRouter(
    prefix="/workspaces/{workspace_id}/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=schemas.ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    workspace_id: int,
    product_data: schemas.ProductCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.PRODUCT_WRITE_ROLES,
    )

    return crud.create_product(product_data, db, workspace_id)


@router.get("", response_model=list[schemas.ProductResponse])
def list_products(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.list_products(
        db=db,
        workspace_id=workspace_id,
        category=category,
        search=search,
        page=page,
        limit=limit,
    )


@router.get("/low-stock", response_model=list[schemas.ProductResponse])
def list_low_stock_products(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.list_low_stock_products(db, workspace_id, page, limit)


@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_workspace_product(
    workspace_id: int,
    product_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.get_product_by_id(product_id, db, workspace_id)


@router.patch("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    workspace_id: int,
    product_id: int,
    product_data: schemas.ProductUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.PRODUCT_WRITE_ROLES,
    )

    return crud.update_product(product_id, product_data, db, workspace_id)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    workspace_id: int,
    product_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.PRODUCT_WRITE_ROLES,
    )
    crud.delete_product(product_id, db, workspace_id)

    return None


@router.post(
    "/{product_id}/stock",
    response_model=schemas.StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    workspace_id: int,
    product_id: int,
    movement_data: schemas.StockMovementCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_WRITE_ROLES,
    )

    return crud.create_stock_movement(
        workspace_id,
        product_id,
        movement_data,
        db,
        user_id=current_user.id,
    )


@router.get(
    "/{product_id}/stock-movements",
    response_model=list[schemas.StockMovementResponse],
)
def list_product_stock_movements(
    workspace_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.list_product_stock_movements(
        product_id,
        db,
        workspace_id,
        page,
        limit,
    )
