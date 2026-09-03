"""crud.dashboard — split from the former monolithic crud.py."""
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

def get_dashboard_summary(db: Session, workspace_id: int):
    product_summary = (
        db.query(
            func.count(models.Product.id).label("total_products"),
            func.coalesce(func.sum(models.Product.quantity), 0).label(
                "total_stock_quantity"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (models.Product.quantity == 0, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("out_of_stock_products"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                models.Product.quantity > 0,
                                models.Product.quantity
                                < models.Product.minimum_quantity,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("low_stock_products"),
        )
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .one()
    )

    total_categories = (
        db.query(func.count(models.Category.id))
        .filter(models.Category.workspace_id == workspace_id)
        .filter(models.Category.is_active.is_(True))
        .scalar()
    )

    total_stock_movements = (
        db.query(func.count(models.StockMovement.id))
        .filter(models.StockMovement.workspace_id == workspace_id)
        .scalar()
    )

    return {
        "total_products": int(product_summary.total_products or 0),
        "total_categories": int(total_categories or 0),
        "low_stock_products": int(product_summary.low_stock_products or 0),
        "out_of_stock_products": int(
            product_summary.out_of_stock_products or 0
        ),
        "total_stock_quantity": int(product_summary.total_stock_quantity or 0),
        "total_stock_movements": int(total_stock_movements or 0),
    }

def list_dashboard_attention_products(
    db: Session,
    workspace_id: int,
    limit: int = 6,
):
    limit = min(max(limit, 1), 100)
    priority_order = case(
        (models.Product.quantity == 0, 0),
        else_=1,
    )
    relative_quantity = case(
        (
            models.Product.minimum_quantity > 0,
            cast(models.Product.quantity, Float)
            / cast(models.Product.minimum_quantity, Float),
        ),
        else_=0.0,
    )

    return (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .filter(
            or_(
                models.Product.quantity == 0,
                models.Product.quantity < models.Product.minimum_quantity,
            )
        )
        .order_by(
            priority_order.asc(),
            relative_quantity.asc(),
            models.Product.quantity.asc(),
            models.Product.name.asc(),
            models.Product.id.asc(),
        )
        .limit(limit)
        .all()
    )

def list_dashboard_recent_activity(
    db: Session,
    workspace_id: int,
    limit: int = 6,
):
    limit = min(max(limit, 1), 100)

    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.workspace_id == workspace_id)
        .order_by(
            models.AuditLog.created_at.desc(),
            models.AuditLog.id.desc(),
        )
        .limit(limit)
        .all()
    )

def get_dashboard(
    db: Session,
    workspace_id: int,
    include_recent_activity: bool = False,
    attention_limit: int = 6,
    activity_limit: int = 6,
):
    recent_activity = (
        list_dashboard_recent_activity(db, workspace_id, activity_limit)
        if include_recent_activity
        else []
    )

    return {
        "summary": get_dashboard_summary(db, workspace_id),
        "attention_products": list_dashboard_attention_products(
            db,
            workspace_id,
            attention_limit,
        ),
        "recent_activity": recent_activity,
    }
