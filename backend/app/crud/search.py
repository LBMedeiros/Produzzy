"""crud.search — split from the former monolithic crud.py."""
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

def search_workspace(db: Session, workspace_id: int, query_text: str, limit: int = 5):
    normalized_query = query_text.strip()

    if len(normalized_query) < 2:
        return {
            "products": [],
            "replenishments": [],
        }

    like_query = f"%{normalized_query}%"
    numeric_product_id = None

    if normalized_query.isdigit():
        numeric_product_id = int(normalized_query.lstrip("0") or "0")

    product_filters = [
        models.Product.name.ilike(like_query),
        models.Product.category.ilike(like_query),
        cast(models.Product.id, String).ilike(like_query),
    ]

    if numeric_product_id:
        product_filters.append(models.Product.id == numeric_product_id)

    products = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .filter(or_(*product_filters))
        .order_by(models.Product.name.asc())
        .limit(limit)
        .all()
    )

    status_labels = {
        schemas.ReplenishmentStatus.open.value: "Necessário repor",
        schemas.ReplenishmentStatus.in_progress.value: "Em andamento",
        schemas.ReplenishmentStatus.completed.value: "Pronto para estocar",
        schemas.ReplenishmentStatus.stocked.value: "Estocado",
        schemas.ReplenishmentStatus.canceled.value: "Cancelada",
    }
    normalized_status_query = normalize_search_value(normalized_query)
    matching_statuses = [
        status_value
        for status_value, label in status_labels.items()
        if normalized_status_query in normalize_search_value(status_value)
        or normalized_status_query in normalize_search_value(label)
    ]

    replenishment_filters = [
        models.Product.name.ilike(like_query),
        models.Product.category.ilike(like_query),
        cast(models.Product.id, String).ilike(like_query),
        models.ReplenishmentRequest.status.ilike(like_query),
    ]

    if numeric_product_id:
        replenishment_filters.append(models.Product.id == numeric_product_id)

    if matching_statuses:
        replenishment_filters.append(
            models.ReplenishmentRequest.status.in_(matching_statuses)
        )

    replenishments = (
        db.query(models.ReplenishmentRequest)
        .join(models.ReplenishmentRequest.product)
        .filter(models.ReplenishmentRequest.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .filter(or_(*replenishment_filters))
        .order_by(models.ReplenishmentRequest.updated_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "products": [
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "code": str(product.id).zfill(9),
                "quantity": product.quantity,
                "minimum_quantity": product.minimum_quantity,
            }
            for product in products
        ],
        "replenishments": [
            {
                "id": replenishment.id,
                "product_id": replenishment.product_id,
                "product_name": replenishment.product_name,
                "product_category": replenishment.product_category,
                "product_code": str(replenishment.product_id).zfill(9),
                "status": replenishment.status,
                "quantity_needed": replenishment.quantity_needed,
            }
            for replenishment in replenishments
        ],
    }
