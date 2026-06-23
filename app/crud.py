from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas


def get_product_by_id(product_id: int, db: Session):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    return product


def get_product_by_name(name: str, db: Session):
    return (
        db.query(models.Product)
        .filter(models.Product.name == name)
        .first()
    )


def create_product(product_data: schemas.ProductCreate, db: Session):
    existing_product = get_product_by_name(product_data.name, db)

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um produto com esse nome.",
        )

    new_product = models.Product(
        name=product_data.name,
        category=product_data.category,
        quantity=product_data.quantity,
        minimum_quantity=product_data.minimum_quantity,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


def list_products(
    db: Session,
    category: str | None = None,
    search: str | None = None,
):
    query = db.query(models.Product)

    if category:
        query = query.filter(models.Product.category.ilike(f"%{category}%"))

    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))

    return query.order_by(models.Product.name.asc()).all()


def list_low_stock_products(db: Session):
    return (
        db.query(models.Product)
        .filter(models.Product.quantity <= models.Product.minimum_quantity)
        .order_by(models.Product.quantity.asc())
        .all()
    )


def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session,
):
    product = get_product_by_id(product_id, db)

    update_data = product_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


def delete_product(product_id: int, db: Session):
    product = get_product_by_id(product_id, db)

    db.delete(product)
    db.commit()

    return None


def create_stock_movement(
    product_id: int,
    movement_data: schemas.StockMovementCreate,
    db: Session,
):
    product = get_product_by_id(product_id, db)

    quantity_before = product.quantity

    if movement_data.movement_type == schemas.StockMovementType.entrada:
        quantity_after = quantity_before + movement_data.quantity

    elif movement_data.movement_type == schemas.StockMovementType.saida:
        if movement_data.quantity > quantity_before:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantidade de saída maior que o estoque atual.",
            )

        quantity_after = quantity_before - movement_data.quantity

    elif movement_data.movement_type == schemas.StockMovementType.ajuste:
        quantity_after = movement_data.quantity

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de movimentação inválido.",
        )

    product.quantity = quantity_after

    movement = models.StockMovement(
        product_id=product.id,
        movement_type=movement_data.movement_type.value,
        quantity=movement_data.quantity,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=movement_data.reason,
    )

    db.add(movement)
    db.commit()
    db.refresh(movement)

    return movement


def list_product_stock_movements(product_id: int, db: Session):
    product = get_product_by_id(product_id, db)

    return (
        db.query(models.StockMovement)
        .filter(models.StockMovement.product_id == product.id)
        .order_by(models.StockMovement.created_at.desc())
        .all()
    )