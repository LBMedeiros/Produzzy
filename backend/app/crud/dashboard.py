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

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception

DASHBOARD_DEFAULT_TIMEZONE = "America/Sao_Paulo"
DASHBOARD_CHART_DAYS = 7
# An in-progress replenishment with no update for this long is "parada".
STALLED_REPLENISHMENT_AFTER = timedelta(days=3)
ACTIVE_REPLENISHMENT_STATUSES = ("open", "in_progress", "completed")

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

    replenished_product_ids = (
        db.query(models.ReplenishmentRequest.product_id)
        .filter(models.ReplenishmentRequest.workspace_id == workspace_id)
        .filter(
            models.ReplenishmentRequest.status.in_(ACTIVE_REPLENISHMENT_STATUSES)
        )
    )
    active_products = (
        db.query(func.count(models.Product.id))
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
    )
    low_stock_in_replenishment = (
        active_products.filter(models.Product.quantity > 0)
        .filter(models.Product.quantity < models.Product.minimum_quantity)
        .filter(models.Product.id.in_(replenished_product_ids))
        .scalar()
    )
    out_of_stock_without_replenishment = (
        active_products.filter(models.Product.quantity == 0)
        .filter(~models.Product.id.in_(replenished_product_ids))
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
        "low_stock_in_replenishment": int(low_stock_in_replenishment or 0),
        "out_of_stock_without_replenishment": int(
            out_of_stock_without_replenishment or 0
        ),
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

def resolve_dashboard_timezone(name: str | None):
    if ZoneInfo is not None:
        for candidate in (name, DASHBOARD_DEFAULT_TIMEZONE):
            if not candidate:
                continue
            try:
                return ZoneInfo(candidate)
            except (ZoneInfoNotFoundError, ValueError, KeyError):
                continue

    # No tz database available: Brasília time has no DST since 2019.
    return timezone(timedelta(hours=-3))


def list_dashboard_movements_by_day(
    db: Session,
    workspace_id: int,
    tz,
    now: datetime | None = None,
    days: int = DASHBOARD_CHART_DAYS,
):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    first_day = today - timedelta(days=days - 1)
    # A day of margin either side covers every UTC offset; buckets use the
    # local date below.
    since = datetime.combine(first_day, datetime.min.time(), tz) - timedelta(days=1)

    rows = (
        db.query(
            models.StockMovement.created_at,
            models.StockMovement.quantity_before,
            models.StockMovement.quantity_after,
        )
        .filter(models.StockMovement.workspace_id == workspace_id)
        .filter(models.StockMovement.created_at >= since)
        .all()
    )

    buckets = {
        first_day + timedelta(days=offset): {"entries": 0, "exits": 0, "total": 0}
        for offset in range(days)
    }

    for created_at, quantity_before, quantity_after in rows:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        bucket = buckets.get(created_at.astimezone(tz).date())

        if bucket is None:
            continue

        bucket["total"] += 1
        if quantity_after > quantity_before:
            bucket["entries"] += 1
        elif quantity_after < quantity_before:
            bucket["exits"] += 1

    return [{"date": day, **counts} for day, counts in sorted(buckets.items())]


def _replenishment_query(db: Session, workspace_id: int):
    return (
        db.query(models.ReplenishmentRequest)
        .options(
            joinedload(models.ReplenishmentRequest.product),
            joinedload(models.ReplenishmentRequest.created_by_user),
            joinedload(models.ReplenishmentRequest.assigned_to_user),
            joinedload(models.ReplenishmentRequest.assignees).joinedload(
                models.ReplenishmentAssignee.user
            ),
        )
        .filter(models.ReplenishmentRequest.workspace_id == workspace_id)
    )


def list_dashboard_stalled_replenishments(
    db: Session,
    workspace_id: int,
    now: datetime | None = None,
    limit: int = 5,
):
    now = now or datetime.now(timezone.utc)

    return (
        _replenishment_query(db, workspace_id)
        .filter(models.ReplenishmentRequest.status == "in_progress")
        .filter(
            models.ReplenishmentRequest.updated_at
            <= now - STALLED_REPLENISHMENT_AFTER
        )
        .order_by(
            models.ReplenishmentRequest.updated_at.asc(),
            models.ReplenishmentRequest.id.asc(),
        )
        .limit(limit)
        .all()
    )


def list_dashboard_ready_replenishments(
    db: Session,
    workspace_id: int,
    limit: int = 5,
):
    return (
        _replenishment_query(db, workspace_id)
        .filter(models.ReplenishmentRequest.status == "completed")
        .order_by(
            models.ReplenishmentRequest.completed_at.desc().nullslast(),
            models.ReplenishmentRequest.id.desc(),
        )
        .limit(limit)
        .all()
    )


def attach_active_replenishments(db: Session, workspace_id: int, products):
    product_ids = [product.id for product in products]
    active_by_product = {}

    if product_ids:
        requests = (
            db.query(
                models.ReplenishmentRequest.product_id,
                models.ReplenishmentRequest.id,
                models.ReplenishmentRequest.status,
            )
            .filter(models.ReplenishmentRequest.workspace_id == workspace_id)
            .filter(models.ReplenishmentRequest.product_id.in_(product_ids))
            .filter(
                models.ReplenishmentRequest.status.in_(
                    ACTIVE_REPLENISHMENT_STATUSES
                )
            )
            .order_by(models.ReplenishmentRequest.id.desc())
            .all()
        )
        for product_id, request_id, request_status in requests:
            active_by_product.setdefault(product_id, (request_id, request_status))

    for product in products:
        request_id, request_status = active_by_product.get(product.id, (None, None))
        product.active_replenishment_id = request_id
        product.active_replenishment_status = request_status

    return products


def attach_activity_names(db: Session, workspace_id: int, logs):
    user_ids = {log.user_id for log in logs if log.user_id}
    product_ids = set()

    for log in logs:
        metadata = log.metadata_json or {}
        if log.entity_type == "product" and log.entity_id:
            product_ids.add(log.entity_id)
        elif isinstance(metadata.get("product_id"), int):
            product_ids.add(metadata["product_id"])

    users = {}
    if user_ids:
        users = {
            user.id: user
            for user in db.query(models.User).filter(models.User.id.in_(user_ids))
        }

    product_names = {}
    if product_ids:
        # Workspace-scoped; deleted products keep their name in the history.
        product_names = dict(
            db.query(models.Product.id, models.Product.name)
            .filter(models.Product.workspace_id == workspace_id)
            .filter(models.Product.id.in_(product_ids))
            .all()
        )

    for log in logs:
        metadata = log.metadata_json or {}
        user = users.get(log.user_id)
        product_id = (
            log.entity_id if log.entity_type == "product" else metadata.get("product_id")
        )
        log.user_name = user.name if user else None
        log.user_avatar_url = getattr(user, "avatar_url", None) if user else None
        log.product_name = (
            metadata.get("product_name")
            or (metadata.get("name") if log.entity_type == "product" else None)
            or product_names.get(product_id)
        )

    return logs


def get_dashboard(
    db: Session,
    workspace_id: int,
    include_recent_activity: bool = False,
    attention_limit: int = 6,
    activity_limit: int = 6,
    tz_name: str | None = None,
):
    tz = resolve_dashboard_timezone(tz_name)
    recent_activity = (
        attach_activity_names(
            db,
            workspace_id,
            list_dashboard_recent_activity(db, workspace_id, activity_limit),
        )
        if include_recent_activity
        else []
    )
    movements_by_day = list_dashboard_movements_by_day(db, workspace_id, tz)
    summary = get_dashboard_summary(db, workspace_id)
    summary["movements_today"] = movements_by_day[-1]["total"]
    summary["movements_yesterday"] = movements_by_day[-2]["total"]

    return {
        "summary": summary,
        "attention_products": attach_active_replenishments(
            db,
            workspace_id,
            list_dashboard_attention_products(db, workspace_id, attention_limit),
        ),
        "recent_activity": recent_activity,
        "movements_by_day": movements_by_day,
        "stalled_replenishments": list_dashboard_stalled_replenishments(
            db, workspace_id
        ),
        "ready_replenishments": list_dashboard_ready_replenishments(
            db, workspace_id
        ),
    }
