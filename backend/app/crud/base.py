"""crud.base — split from the former monolithic crud.py."""
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from time import perf_counter

from sqlalchemy import Float, String, and_, case, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.errors import *  # noqa: F401,F403 -- re-exported to every crud module
from app.services.security_service import get_password_hash, verify_password

# Access levels (`WorkspaceMember.role`), from most to least access:
#   owner     — "Responsável pelo workspace" (crown); full access, any cargo.
#   admin     — Administração: everything, including members, cargos, invites.
#   manager   — Gestão: everything except members, cargos and invites.
#   employee  — Operação: stock movements and replenishment work.
#   requester — Solicitante: read access plus opening replenishment needs.
#   viewer    — Visualizador: read-only (shareable invite links).
READ_ROLES = {"owner", "admin", "manager", "employee", "requester", "viewer"}
PRODUCT_WRITE_ROLES = {"owner", "admin", "manager"}
CATEGORY_WRITE_ROLES = {"owner", "admin", "manager"}
STOCK_WRITE_ROLES = {"owner", "admin", "manager", "employee"}
REPLENISHMENT_CREATE_ROLES = {"owner", "admin", "manager", "employee", "requester"}
REPLENISHMENT_UPDATE_ROLES = {"owner", "admin", "manager", "employee"}
REPLENISHMENT_ASSIGN_ROLES = {"owner", "admin", "manager", "employee"}
# Who can be responsible for (assigned to) a replenishment: Operação and up.
REPLENISHMENT_ASSIGNEE_ROLES = {"owner", "admin", "manager", "employee"}
REPLENISHMENT_MANAGE_ASSIGNEES_ROLES = {"owner", "admin", "manager"}
MEMBER_MANAGE_ROLES = {"owner", "admin"}
MEMBER_ROLE_UPDATE_ROLES = {"owner", "admin"}
INVITE_MANAGE_ROLES = {"owner", "admin"}
AUDIT_LOG_READ_ROLES = {"owner", "admin", "manager"}
# Levels an admin may manage (assign, invite, remove). Admin-level cargos are
# assigned only by the workspace owner.
ADMIN_MEMBER_TARGET_ROLES = {"manager", "employee", "requester", "viewer"}
ADMIN_MANAGE_TARGET_DENIED = (
    "Admin só gerencia membros de Gestão, Operação, Solicitante ou Visualizador."
)
MEMBER_TITLE_MANAGE_ROLES = {"owner", "admin"}

# Fixed catalog of cargos. The cargo defines the member's access level
# (`role`); the owner keeps full access whatever cargo they pick.
# Mirrored in the frontend (lib/formatters.js: memberTitleOptions); keep in sync.
WORKSPACE_MEMBER_TITLE_ROLES = {
    "CEO": "admin",
    "Sócio": "admin",
    "Gerente": "admin",
    "Supervisor": "manager",
    "Coordenador": "manager",
    "Secretário(a)": "manager",
    "Produção": "employee",
    "Estoquista": "employee",
    "Financeiro": "requester",
    "Comprador": "requester",
    "Vendedor": "requester",
    "Assistente": "requester",
    "Atendente": "requester",
    "Visualizador": "viewer",
}
WORKSPACE_MEMBER_TITLES = tuple(WORKSPACE_MEMBER_TITLE_ROLES)
# Cargo given to people who join through a shareable (viewer-only) link.
INVITE_LINK_MEMBER_TITLE = "Visualizador"
ACTIVE_PRODUCT_NAME_EXISTS = (
    "Já existe um produto ativo com esse nome neste workspace."
)
ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS = (
    "Já existe outro produto ativo com esse nome neste workspace."
)
DUPLICATE_CATEGORY_NAME = "Já existe uma categoria com esse nome neste workspace."
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
# Placeholder address of an individual invite created without an e-mail.
OPEN_INVITE_EMAIL_DOMAIN = "open-invite.produzzy.local"

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
        raise NotFound("Workspace não encontrado.")

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
        raise PermissionDenied("Usuário não é membro deste workspace.")

    return member

def require_workspace_role(
    workspace_id: int,
    current_user: models.User,
    db: Session,
    allowed_roles: set[str],
):
    member = require_workspace_member(workspace_id, current_user, db)

    if member.role not in allowed_roles:
        raise PermissionDenied("Permissão insuficiente neste workspace.")

    return member


def normalize_member_title(title):
    if title is None:
        return None

    normalized = str(title).strip()

    if not normalized:
        return None

    if normalized not in WORKSPACE_MEMBER_TITLES:
        raise ValidationError("Cargo inválido.")

    return normalized


def get_title_role(title: str | None) -> str | None:
    """Access level granted by a cargo (None for no/unknown cargo)."""
    return WORKSPACE_MEMBER_TITLE_ROLES.get(title) if title else None
