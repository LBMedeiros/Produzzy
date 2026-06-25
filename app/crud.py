from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.security_service import get_password_hash, verify_password


def normalize_email(email: str):
    return email.strip().lower()


def get_user_by_email(email: str, db: Session):
    return (
        db.query(models.User)
        .filter(models.User.email == normalize_email(email))
        .first()
    )


def create_user(user_data: schemas.UserCreate, db: Session):
    email = normalize_email(user_data.email)
    existing_user = get_user_by_email(email, db)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário com esse e-mail.",
        )

    new_user = models.User(
        name=user_data.name.strip(),
        email=email,
        hashed_password=get_password_hash(user_data.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def authenticate_user(login_data: schemas.UserLogin, db: Session):
    user = get_user_by_email(login_data.email, db)

    if not user or not verify_password(
        login_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo.",
        )

    return user


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

def normalize_category_name(name: str):
    return name.strip()


def get_category_by_id(category_id: int, db: Session):
    category = (
        db.query(models.Category)
        .filter(models.Category.id == category_id)
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )

    return category


def get_category_by_name(name: str, db: Session):
    normalized_name = normalize_category_name(name)

    return (
        db.query(models.Category)
        .filter(models.Category.name == normalized_name)
        .first()
    )


def create_category(category_data: schemas.CategoryCreate, db: Session):
    name = normalize_category_name(category_data.name)

    existing_category = get_category_by_name(name, db)

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma categoria com esse nome.",
        )

    new_category = models.Category(
        name=name,
        description=category_data.description,
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return new_category


def list_categories(db: Session, search: str | None = None):
    query = db.query(models.Category)

    if search:
        query = query.filter(models.Category.name.ilike(f"%{search}%"))

    return query.order_by(models.Category.name.asc()).all()


def update_category(
    category_id: int,
    category_data: schemas.CategoryUpdate,
    db: Session,
):
    category = get_category_by_id(category_id, db)

    update_data = category_data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = normalize_category_name(update_data["name"])

        existing_category = get_category_by_name(new_name, db)

        if existing_category and existing_category.id != category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com esse nome.",
            )

        update_data["name"] = new_name

    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    return category


def delete_category(category_id: int, db: Session):
    category = get_category_by_id(category_id, db)

    db.delete(category)
    db.commit()

    return None