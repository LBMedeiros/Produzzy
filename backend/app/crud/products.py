"""crud.products — split from the former monolithic crud.py."""
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from time import perf_counter

from fastapi import HTTPException, status
from sqlalchemy import Float, String, and_, case, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.services.security_service import get_password_hash, verify_password
from app.crud.base import *  # noqa: F401,F403
from app.crud.categories import get_category_by_id, get_category_by_name

def normalize_product_status(product_status):
    if hasattr(product_status, "value"):
        return product_status.value

    return str(product_status)

def get_product_by_id(
    product_id: int,
    db: Session,
    workspace_id: int | None = None,
    include_deleted: bool = False,
    for_update: bool = False,
):
    query = db.query(models.Product).filter(models.Product.id == product_id)

    if workspace_id is None:
        query = query.filter(models.Product.workspace_id.is_(None))
    else:
        query = query.filter(models.Product.workspace_id == workspace_id)

    if not include_deleted:
        query = query.filter(models.Product.is_active.is_(True))

    if for_update and db.bind is not None and db.bind.dialect.name != "sqlite":
        query = query.with_for_update()

    product = query.first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    return product

def get_product_by_name(
    name: str,
    workspace_id: int,
    db: Session,
    only_active: bool = False,
):
    query = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.name == name)
    )

    if only_active:
        query = query.filter(models.Product.is_active.is_(True))

    return query.first()

def resolve_category_id(name: str, workspace_id: int, db: Session):
    """Best-effort link of a product's category name to its Category row.

    Returns None when no active category with that name exists in the
    workspace (arbitrary strings from non-UI clients stay unlinked).
    """
    category = get_category_by_name(name, db, workspace_id, only_active=True)

    return category.id if category else None

def create_product(
    product_data: schemas.ProductCreate,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    name = product_data.name.strip()
    existing_product = get_product_by_name(
        name,
        workspace_id,
        db,
        only_active=True,
    )

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ACTIVE_PRODUCT_NAME_EXISTS,
        )

    category_name = product_data.category.strip()
    new_product = models.Product(
        workspace_id=workspace_id,
        name=name,
        category=category_name,
        category_id=resolve_category_id(category_name, workspace_id, db),
        quantity=product_data.quantity,
        minimum_quantity=product_data.minimum_quantity,
    )

    db.add(new_product)
    db.flush()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="product.created",
        entity_type="product",
        entity_id=new_product.id,
        metadata={
            "name": new_product.name,
            "category": new_product.category,
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ACTIVE_PRODUCT_NAME_EXISTS,
        )

    db.refresh(new_product)

    return new_product

def list_products(
    db: Session,
    workspace_id: int,
    category: str | None = None,
    search: str | None = None,
    product_status: schemas.ProductStatus | str = schemas.ProductStatus.active,
    page: int = 1,
    limit: int = 20,
):
    query = db.query(models.Product).filter(
        models.Product.workspace_id == workspace_id
    )
    status_value = normalize_product_status(product_status)

    if status_value == schemas.ProductStatus.active.value:
        query = query.filter(models.Product.is_active.is_(True))
    elif status_value == schemas.ProductStatus.deleted.value:
        query = query.filter(models.Product.is_active.is_(False))
    elif status_value != schemas.ProductStatus.all.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status de produto inválido.",
        )

    if category:
        query = query.filter(models.Product.category.ilike(f"%{category}%"))

    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))

    query = query.order_by(models.Product.name.asc())

    return paginate_query(query, page, limit).all()

def list_low_stock_products(
    db: Session,
    workspace_id: int,
    page: int = 1,
    limit: int = 20,
):
    query = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .filter(models.Product.quantity > 0)
        .filter(models.Product.quantity < models.Product.minimum_quantity)
        .order_by(models.Product.quantity.asc())
    )

    return paginate_query(query, page, limit).all()

def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    product = get_product_by_id(product_id, db, workspace_id)

    update_data = product_data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = update_data["name"].strip()
        existing_product = get_product_by_name(
            new_name,
            workspace_id,
            db,
            only_active=True,
        )

        if existing_product and existing_product.id != product.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
            )

        update_data["name"] = new_name

    if "category" in update_data:
        update_data["category"] = update_data["category"].strip()
        product.category_id = resolve_category_id(
            update_data["category"],
            workspace_id,
            db,
        )

    for field, value in update_data.items():
        setattr(product, field, value)

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="product.updated",
        entity_type="product",
        entity_id=product.id,
        metadata={
            "name": product.name,
            "fields": sorted(update_data.keys()),
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
        )

    db.refresh(product)

    return product

def delete_product(
    product_id: int,
    db: Session,
    workspace_id: int,
    deleted_by_user_id: int,
):
    product = get_product_by_id(
        product_id,
        db,
        workspace_id,
        include_deleted=True,
    )

    if not product.is_active:
        return product

    product.is_active = False
    product.deleted_at = aware_utc_now()
    product.deleted_by_user_id = deleted_by_user_id
    product.deleted_by_category_id = None
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=deleted_by_user_id,
        action="product.deleted",
        entity_type="product",
        entity_id=product.id,
        metadata={"name": product.name},
    )

    db.commit()
    db.refresh(product)

    return product

def restore_product(
    product_id: int,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    product = get_product_by_id(
        product_id,
        db,
        workspace_id,
        include_deleted=True,
    )

    if product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O produto já está ativo.",
        )

    if product.deleted_by_category_id is not None:
        deleted_category = get_category_by_id(
            product.deleted_by_category_id,
            db,
            workspace_id,
            include_deleted=True,
        )

        if not deleted_category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Restaure a categoria antes de restaurar este produto.",
            )

    existing_product = get_product_by_name(
        product.name,
        workspace_id,
        db,
        only_active=True,
    )

    if existing_product and existing_product.id != product.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
        )

    product.is_active = True
    product.deleted_at = None
    product.deleted_by_user_id = None
    product.deleted_by_category_id = None
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="product.restored",
        entity_type="product",
        entity_id=product.id,
        metadata={"name": product.name},
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
        )

    db.refresh(product)

    return product
