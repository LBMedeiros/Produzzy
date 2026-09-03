"""crud.stock — split from the former monolithic crud.py."""
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
from app.crud.products import get_product_by_id
from app.crud.replenishment import (
    get_replenishment_request_by_id,
    replenishment_metadata,
)

def create_stock_movement(
    workspace_id: int,
    product_id: int,
    movement_data: schemas.StockMovementCreate,
    db: Session,
    user_id: int | None = None,
):
    product = get_product_by_id(
        product_id,
        db,
        workspace_id,
        include_deleted=True,
        for_update=True,
    )

    if not product.is_active:
        raise ValidationError("Não é possível movimentar estoque de um produto inativo.")

    replenishment_request = None

    if movement_data.replenishment_request_id is not None:
        replenishment_request = get_replenishment_request_by_id(
            workspace_id,
            movement_data.replenishment_request_id,
            db,
        )

        if replenishment_request.product_id != product.id:
            raise ValidationError("A necessidade de reposição não pertence a este produto.")

        if movement_data.movement_type != schemas.StockMovementType.entrada:
            raise ValidationError("Uma reposição só pode ser vinculada a uma entrada.")

        if (
            replenishment_request.status
            != schemas.ReplenishmentStatus.completed.value
        ):
            raise ValidationError("A necessidade não está pronta para estocar.")

    quantity_before = product.quantity

    if (
        movement_data.movement_type != schemas.StockMovementType.ajuste
        and movement_data.quantity <= 0
    ):
        raise ValidationError("A quantidade da movimentação precisa ser maior que zero.")

    if movement_data.movement_type == schemas.StockMovementType.entrada:
        quantity_after = quantity_before + movement_data.quantity

    elif movement_data.movement_type == schemas.StockMovementType.saida:
        if movement_data.quantity > quantity_before:
            raise ValidationError("Quantidade de saída maior que o estoque atual.")

        quantity_after = quantity_before - movement_data.quantity

    elif movement_data.movement_type == schemas.StockMovementType.ajuste:
        quantity_after = movement_data.quantity

    else:
        raise ValidationError("Tipo de movimentação inválido.")

    product.quantity = quantity_after

    movement = models.StockMovement(
        workspace_id=workspace_id,
        product_id=product.id,
        user_id=user_id,
        movement_type=movement_data.movement_type.value,
        quantity=movement_data.quantity,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=movement_data.reason,
    )

    db.add(movement)
    db.flush()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="stock.movement_created",
        entity_type="stock_movement",
        entity_id=movement.id,
        metadata={
            "product_id": product.id,
            "movement_type": movement.movement_type,
            "quantity": movement.quantity,
            "quantity_before": movement.quantity_before,
            "quantity_after": movement.quantity_after,
        },
    )

    if replenishment_request is not None:
        replenishment_request.status = schemas.ReplenishmentStatus.stocked.value
        replenishment_request.updated_at = aware_utc_now()
        create_audit_log(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            action="replenishment.stocked",
            entity_type="replenishment_request",
            entity_id=replenishment_request.id,
            metadata=replenishment_metadata(replenishment_request),
        )

    db.commit()
    db.refresh(movement)

    return movement

def list_product_stock_movements(
    product_id: int,
    db: Session,
    workspace_id: int,
    page: int = 1,
    limit: int = 20,
):
    product = get_product_by_id(
        product_id,
        db,
        workspace_id,
        include_deleted=True,
    )

    query = (
        db.query(models.StockMovement)
        .options(joinedload(models.StockMovement.user))
        .filter(models.StockMovement.workspace_id == workspace_id)
        .filter(models.StockMovement.product_id == product.id)
        .order_by(models.StockMovement.created_at.desc())
    )

    return paginate_query(query, page, limit).all()

def list_workspace_stock_movements(
    db: Session,
    workspace_id: int,
    page: int = 1,
    limit: int = 20,
):
    query = (
        db.query(models.StockMovement)
        .options(
            joinedload(models.StockMovement.product),
            joinedload(models.StockMovement.user),
        )
        .filter(models.StockMovement.workspace_id == workspace_id)
        .order_by(models.StockMovement.created_at.desc())
    )

    return paginate_query(query, page, limit).all()
