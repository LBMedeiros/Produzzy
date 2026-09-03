"""crud.categories — split from the former monolithic crud.py."""
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from time import perf_counter

from sqlalchemy import Float, String, and_, case, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.services.security_service import get_password_hash, verify_password
from app.crud.base import *  # noqa: F401,F403

def normalize_category_status(category_status):
    if hasattr(category_status, "value"):
        return category_status.value

    return str(category_status)

def normalize_category_name(name: str):
    return name.strip()

def get_category_by_id(
    category_id: int,
    db: Session,
    workspace_id: int | None = None,
    include_deleted: bool = False,
):
    query = db.query(models.Category).filter(models.Category.id == category_id)

    if workspace_id is None:
        query = query.filter(models.Category.workspace_id.is_(None))
    else:
        query = query.filter(models.Category.workspace_id == workspace_id)

    if not include_deleted:
        query = query.filter(models.Category.is_active.is_(True))

    category = query.first()

    if not category:
        raise NotFound("Categoria não encontrada.")

    return category

def get_category_by_name(
    name: str,
    db: Session,
    workspace_id: int,
    only_active: bool = False,
):
    normalized_name = normalize_category_name(name)

    query = (
        db.query(models.Category)
        .filter(models.Category.workspace_id == workspace_id)
        .filter(models.Category.name == normalized_name)
    )

    if only_active:
        query = query.filter(models.Category.is_active.is_(True))

    return query.first()

def create_category(
    category_data: schemas.CategoryCreate,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    name = normalize_category_name(category_data.name)

    existing_category = get_category_by_name(
        name,
        db,
        workspace_id,
        only_active=True,
    )

    if existing_category:
        raise ValidationError("Já existe uma categoria com esse nome neste workspace.")

    new_category = models.Category(
        workspace_id=workspace_id,
        name=name,
        description=category_data.description,
    )

    db.add(new_category)
    db.flush()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="category.created",
        entity_type="category",
        entity_id=new_category.id,
        metadata={"name": new_category.name},
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValidationError(
            "Não foi possível criar a categoria com esse nome. "
            "No SQLite atual ainda pode existir uma constraint global antiga."
        )

    db.refresh(new_category)

    return new_category

def list_categories(
    db: Session,
    workspace_id: int,
    search: str | None = None,
    category_status: schemas.CategoryStatus | str = schemas.CategoryStatus.active,
    page: int = 1,
    limit: int = 20,
):
    query = db.query(models.Category).filter(
        models.Category.workspace_id == workspace_id
    )
    status_value = normalize_category_status(category_status)

    if status_value == schemas.CategoryStatus.active.value:
        query = query.filter(models.Category.is_active.is_(True))
    elif status_value == schemas.CategoryStatus.deleted.value:
        query = query.filter(models.Category.is_active.is_(False))
    elif status_value != schemas.CategoryStatus.all.value:
        raise ValidationError("Status de categoria inválido.")

    if search:
        query = query.filter(
            models.Category.name.ilike(f"%{search}%")
            | models.Category.description.ilike(f"%{search}%")
        )

    query = query.order_by(models.Category.name.asc())

    return paginate_query(query, page, limit).all()

def update_category(
    category_id: int,
    category_data: schemas.CategoryUpdate,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    category = get_category_by_id(category_id, db, workspace_id)

    update_data = category_data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = normalize_category_name(update_data["name"])

        existing_category = get_category_by_name(
            new_name,
            db,
            workspace_id,
            only_active=True,
        )

        if existing_category and existing_category.id != category.id:
            raise ValidationError("Já existe uma categoria com esse nome neste workspace.")

        update_data["name"] = new_name

    old_name = category.name

    for field, value in update_data.items():
        setattr(category, field, value)

    if "name" in update_data and category.name != old_name:
        # Keep the denormalized product.category in sync with the rename.
        db.query(models.Product).filter(
            models.Product.workspace_id == workspace_id,
            models.Product.category_id == category.id,
        ).update(
            {models.Product.category: category.name},
            synchronize_session=False,
        )

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="category.updated",
        entity_type="category",
        entity_id=category.id,
        metadata={
            "name": category.name,
            "fields": sorted(update_data.keys()),
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValidationError(
            "Não foi possível atualizar a categoria com esse nome. "
            "No SQLite atual ainda pode existir uma constraint global antiga."
        )

    db.refresh(category)

    return category

def delete_category(
    category_id: int,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    category = get_category_by_id(
        category_id,
        db,
        workspace_id,
        include_deleted=True,
    )

    if not category.is_active:
        return category

    deleted_at = aware_utc_now()
    active_products = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .filter(
            or_(
                models.Product.category_id == category.id,
                and_(
                    models.Product.category_id.is_(None),
                    models.Product.category == category.name,
                ),
            )
        )
        .all()
    )

    for product in active_products:
        product.is_active = False
        product.deleted_at = deleted_at
        product.deleted_by_user_id = user_id
        product.deleted_by_category_id = category.id
        create_audit_log(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            action="product.deleted",
            entity_type="product",
            entity_id=product.id,
            metadata={
                "name": product.name,
                "category_name": category.name,
                "deleted_by_category_id": category.id,
            },
        )

    category.is_active = False
    category.deleted_at = deleted_at
    category.deleted_by_user_id = user_id
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="category.deleted",
        entity_type="category",
        entity_id=category.id,
        metadata={
            "category_name": category.name,
            "linked_products_count": len(active_products),
        },
    )
    db.commit()
    db.refresh(category)

    return category

def restore_category(
    category_id: int,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    category = get_category_by_id(
        category_id,
        db,
        workspace_id,
        include_deleted=True,
    )

    if category.is_active:
        return {
            "category": category,
            "restored_products_count": 0,
            "skipped_products_count": 0,
        }

    existing_category = get_category_by_name(
        category.name,
        db,
        workspace_id,
        only_active=True,
    )

    if existing_category and existing_category.id != category.id:
        raise ValidationError(ANOTHER_ACTIVE_CATEGORY_NAME_EXISTS)

    products_to_restore = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.deleted_by_category_id == category.id)
        .filter(models.Product.is_active.is_(False))
        .order_by(models.Product.id.asc())
        .all()
    )
    active_product_names = {
        name
        for (name,) in (
            db.query(models.Product.name)
            .filter(models.Product.workspace_id == workspace_id)
            .filter(models.Product.is_active.is_(True))
            .all()
        )
    }
    restored_products_count = 0
    skipped_products_count = 0

    category.is_active = True
    category.deleted_at = None
    category.deleted_by_user_id = None

    for product in products_to_restore:
        if product.name in active_product_names:
            skipped_products_count += 1
            continue

        product.is_active = True
        product.deleted_at = None
        product.deleted_by_user_id = None
        product.deleted_by_category_id = None
        product.category_id = category.id
        product.category = category.name
        active_product_names.add(product.name)
        restored_products_count += 1
        create_audit_log(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            action="product.restored",
            entity_type="product",
            entity_id=product.id,
            metadata={
                "name": product.name,
                "category_name": category.name,
                "deleted_by_category_id": category.id,
            },
        )

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="category.restored",
        entity_type="category",
        entity_id=category.id,
        metadata={
            "category_name": category.name,
            "restored_products_count": restored_products_count,
            "skipped_products_count": skipped_products_count,
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValidationError(ANOTHER_ACTIVE_CATEGORY_NAME_EXISTS)

    db.refresh(category)

    return {
        "category": category,
        "restored_products_count": restored_products_count,
        "skipped_products_count": skipped_products_count,
    }
