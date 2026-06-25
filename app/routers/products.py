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

    return crud.create_product(
        product_data,
        db,
        workspace_id,
        user_id=current_user.id,
    )


@router.get("", response_model=list[schemas.ProductResponse])
def list_products(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    category: Optional[str] = None,
    search: Optional[str] = None,
    product_status: schemas.ProductStatus = Query(
        default=schemas.ProductStatus.active,
        alias="status",
    ),
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
        product_status=product_status,
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
    include_deleted: bool = Query(default=False),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.get_product_by_id(
        product_id,
        db,
        workspace_id,
        include_deleted=include_deleted,
    )


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

    return crud.update_product(
        product_id,
        product_data,
        db,
        workspace_id,
        user_id=current_user.id,
    )


@router.delete("/{product_id}", response_model=schemas.ProductResponse)
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
    return crud.delete_product(
        product_id,
        db,
        workspace_id,
        deleted_by_user_id=current_user.id,
    )


@router.post("/{product_id}/restore", response_model=schemas.ProductResponse)
def restore_product(
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

    return crud.restore_product(
        product_id,
        db,
        workspace_id,
        user_id=current_user.id,
    )


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
