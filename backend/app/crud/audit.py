"""crud.audit — split from the former monolithic crud.py."""
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

def list_audit_logs(
    db: Session,
    workspace_id: int,
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = None,
    page: int = 1,
    limit: int = 20,
):
    query = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.workspace_id == workspace_id)
    )

    if action:
        query = query.filter(models.AuditLog.action == action)

    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)

    if user_id:
        query = query.filter(models.AuditLog.user_id == user_id)

    query = query.order_by(models.AuditLog.created_at.desc())

    return paginate_query(query, page, limit).all()
