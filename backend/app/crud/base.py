"""crud.base — split from the former monolithic crud.py."""
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

READ_ROLES = {"owner", "admin", "employee", "viewer"}
PRODUCT_WRITE_ROLES = {"owner", "admin"}
CATEGORY_WRITE_ROLES = {"owner", "admin"}
STOCK_WRITE_ROLES = {"owner", "admin", "employee"}
REPLENISHMENT_CREATE_ROLES = {"owner", "admin", "employee"}
REPLENISHMENT_UPDATE_ROLES = {"owner", "admin", "employee"}
REPLENISHMENT_ASSIGN_ROLES = {"owner", "admin", "employee"}
REPLENISHMENT_MANAGE_ASSIGNEES_ROLES = {"owner", "admin"}
MEMBER_MANAGE_ROLES = {"owner", "admin"}
MEMBER_ROLE_UPDATE_ROLES = {"owner", "admin"}
INVITE_MANAGE_ROLES = {"owner", "admin"}
AUDIT_LOG_READ_ROLES = {"owner", "admin"}
ADMIN_MEMBER_TARGET_ROLES = {"employee", "viewer"}
ACTIVE_PRODUCT_NAME_EXISTS = (
    "Já existe um produto ativo com esse nome neste workspace."
)
ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS = (
    "Já existe outro produto ativo com esse nome neste workspace."
)
ANOTHER_ACTIVE_CATEGORY_NAME_EXISTS = (
    "Já existe outra categoria ativa com esse nome neste workspace."
)
ACTIVE_REPLENISHMENT_EXISTS = (
    "Já existe uma necessidade ativa para este produto."
)
ACTIVE_REPLENISHMENT_INDEX_NAME = "uq_replenishment_requests_active_product"
ACTIVE_REPLENISHMENT_STATUSES = (
    schemas.ReplenishmentStatus.open.value,
    schemas.ReplenishmentStatus.in_progress.value,
    schemas.ReplenishmentStatus.completed.value,
)
INVITE_LINK_EMAIL_DOMAIN = "invite.produzzy.local"

def normalize_search_value(value: str):
    normalized_value = unicodedata.normalize("NFKD", value)

    return "".join(
        char for char in normalized_value if not unicodedata.combining(char)
    ).lower()

def normalize_email(email: str):
    return email.strip().lower()

def normalize_role(role):
    if hasattr(role, "value"):
        return role.value

    return str(role)

def paginate_query(query, page: int = 1, limit: int = 20):
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    offset = (page - 1) * limit

    return query.offset(offset).limit(limit)

def create_audit_log(
    db: Session,
    workspace_id: int | None,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    metadata: dict | None = None,
):
    audit_log = models.AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
    )

    db.add(audit_log)

    return audit_log

def aware_utc_now():
    return datetime.now(timezone.utc)

def is_expired(expires_at: datetime):
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return expires_at < aware_utc_now()

def get_workspace_by_id(workspace_id: int, db: Session):
    workspace = (
        db.query(models.Workspace)
        .filter(models.Workspace.id == workspace_id)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace não encontrado.",
        )

    return workspace

def get_workspace_member(
    workspace_id: int,
    user_id: int,
    db: Session,
):
    return (
        db.query(models.WorkspaceMember)
        .filter(models.WorkspaceMember.workspace_id == workspace_id)
        .filter(models.WorkspaceMember.user_id == user_id)
        .first()
    )

def require_workspace_member(
    workspace_id: int,
    current_user: models.User,
    db: Session,
):
    get_workspace_by_id(workspace_id, db)

    member = get_workspace_member(
        workspace_id=workspace_id,
        user_id=current_user.id,
        db=db,
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não é membro deste workspace.",
        )

    return member

def require_workspace_role(
    workspace_id: int,
    current_user: models.User,
    db: Session,
    allowed_roles: set[str],
):
    member = require_workspace_member(workspace_id, current_user, db)

    if member.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente neste workspace.",
        )

    return member
