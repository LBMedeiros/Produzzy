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


def get_user_by_email(email: str, db: Session):
    return (
        db.query(models.User)
        .filter(models.User.email == normalize_email(email))
        .first()
    )


def get_user_by_provider_user_id(
    auth_provider: str,
    provider_user_id: str,
    db: Session,
):
    return (
        db.query(models.User)
        .filter(models.User.auth_provider == auth_provider)
        .filter(models.User.provider_user_id == provider_user_id)
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
        auth_provider="password",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def elapsed_ms(started_at: float):
    return round((perf_counter() - started_at) * 1000)


def authenticate_user(
    login_data: schemas.UserLogin,
    db: Session,
    auth_timings: dict[str, int] | None = None,
):
    lookup_started_at = perf_counter()
    user = get_user_by_email(login_data.email, db)

    if auth_timings is not None:
        auth_timings["user_lookup_ms"] = elapsed_ms(lookup_started_at)

    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="E-mail ou senha inválidos.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not user.hashed_password:
        if auth_timings is not None:
            auth_timings.setdefault("password_verify_ms", 0)
        raise invalid_credentials_error

    password_verify_started_at = perf_counter()
    is_valid_password = verify_password(login_data.password, user.hashed_password)

    if auth_timings is not None:
        auth_timings["password_verify_ms"] = elapsed_ms(password_verify_started_at)

    if not is_valid_password:
        raise invalid_credentials_error

    if not user.is_active:
        raise invalid_credentials_error

    return user


def is_google_authoritative_for_email(email: str, google_claims: dict):
    normalized_email = normalize_email(email)

    return normalized_email.endswith("@gmail.com") or bool(google_claims.get("hd"))


def authenticate_google_user(google_claims: dict, db: Session):
    provider_user_id = str(google_claims.get("sub") or "").strip()
    email = normalize_email(str(google_claims.get("email") or ""))
    name = str(google_claims.get("name") or "").strip() or email.split("@")[0]

    if not provider_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial do Google inválida.",
        )

    existing_provider_user = get_user_by_provider_user_id(
        "google",
        provider_user_id,
        db,
    )

    if existing_provider_user:
        if not existing_provider_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credencial do Google inválida.",
            )

        return existing_provider_user

    existing_email_user = get_user_by_email(email, db)

    if existing_email_user:
        if not existing_email_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credencial do Google inválida.",
            )

        if existing_email_user.provider_user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este e-mail já está vinculado a outra conta Google.",
            )

        if not is_google_authoritative_for_email(email, google_claims):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Entre com e-mail e senha para vincular este Google "
                    "com segurança."
                ),
            )

        existing_email_user.auth_provider = "google"
        existing_email_user.provider_user_id = provider_user_id
        db.commit()
        db.refresh(existing_email_user)

        return existing_email_user

    new_user = models.User(
        name=name,
        email=email,
        hashed_password=None,
        auth_provider="google",
        provider_user_id=provider_user_id,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def update_current_user_profile(
    current_user: models.User,
    profile_data: schemas.UserProfileUpdate,
    db: Session,
):
    current_user.name = profile_data.name.strip()

    db.commit()
    db.refresh(current_user)

    return current_user


def change_current_user_email(
    current_user: models.User,
    email_data: schemas.UserEmailChange,
    db: Session,
):
    if current_user.auth_provider == "google" and not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A alteração de email para contas Google será disponibilizada "
                "após reautenticação com o provedor."
            ),
        )

    if not current_user.hashed_password or not verify_password(
        email_data.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta.",
        )

    email = normalize_email(email_data.email)
    existing_user = get_user_by_email(email, db)

    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está em uso.",
        )

    current_user.email = email

    db.commit()
    db.refresh(current_user)

    return current_user


def update_current_user_avatar(
    current_user: models.User,
    avatar_url: str,
    avatar_public_id: str,
    db: Session,
):
    previous_public_id = current_user.avatar_public_id

    current_user.avatar_url = avatar_url
    current_user.avatar_public_id = avatar_public_id

    db.commit()
    db.refresh(current_user)

    return current_user, previous_public_id


def clear_current_user_avatar(current_user: models.User, db: Session):
    previous_public_id = current_user.avatar_public_id

    current_user.avatar_url = None
    current_user.avatar_public_id = None

    db.commit()
    db.refresh(current_user)

    return current_user, previous_public_id


def normalize_role(role):
    if hasattr(role, "value"):
        return role.value

    return str(role)


def attach_current_user_role(
    workspace: models.Workspace,
    current_user: models.User,
    db: Session,
):
    membership = (
        db.query(models.WorkspaceMember)
        .filter(models.WorkspaceMember.workspace_id == workspace.id)
        .filter(models.WorkspaceMember.user_id == current_user.id)
        .first()
    )
    workspace.current_user_role = membership.role if membership else None

    return workspace


def attach_current_user_roles(
    workspaces: list[models.Workspace],
    current_user: models.User,
    db: Session,
):
    workspace_ids = [workspace.id for workspace in workspaces]

    if not workspace_ids:
        return workspaces

    memberships = (
        db.query(models.WorkspaceMember)
        .filter(models.WorkspaceMember.workspace_id.in_(workspace_ids))
        .filter(models.WorkspaceMember.user_id == current_user.id)
        .all()
    )
    roles_by_workspace_id = {
        membership.workspace_id: membership.role for membership in memberships
    }

    for workspace in workspaces:
        workspace.current_user_role = roles_by_workspace_id.get(workspace.id)

    return workspaces


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


def normalize_product_status(product_status):
    if hasattr(product_status, "value"):
        return product_status.value

    return str(product_status)


def normalize_category_status(category_status):
    if hasattr(category_status, "value"):
        return category_status.value

    return str(category_status)


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


def list_user_workspaces(
    current_user: models.User,
    db: Session,
    page: int = 1,
    limit: int = 20,
):
    query = (
        db.query(models.Workspace)
        .join(models.WorkspaceMember)
        .filter(models.WorkspaceMember.user_id == current_user.id)
        .order_by(models.Workspace.name.asc())
    )

    workspaces = paginate_query(query, page, limit).all()

    return attach_current_user_roles(workspaces, current_user, db)


def create_workspace(
    workspace_data: schemas.WorkspaceCreate,
    current_user: models.User,
    db: Session,
):
    workspace = models.Workspace(
        name=workspace_data.name.strip(),
        owner_id=current_user.id,
    )

    db.add(workspace)
    db.flush()

    member = models.WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=schemas.WorkspaceRole.owner.value,
    )

    db.add(member)
    create_audit_log(
        db=db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        action="workspace.created",
        entity_type="workspace",
        entity_id=workspace.id,
        metadata={"name": workspace.name},
    )
    db.commit()
    db.refresh(workspace)

    return attach_current_user_role(workspace, current_user, db)


def get_workspace_for_user(
    workspace_id: int,
    current_user: models.User,
    db: Session,
):
    require_workspace_member(workspace_id, current_user, db)

    workspace = get_workspace_by_id(workspace_id, db)

    return attach_current_user_role(workspace, current_user, db)


def update_workspace(
    workspace_id: int,
    workspace_data: schemas.WorkspaceUpdate,
    current_user: models.User,
    db: Session,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        {schemas.WorkspaceRole.owner.value},
    )
    workspace = get_workspace_by_id(workspace_id, db)
    old_name = workspace.name
    workspace.name = workspace_data.name.strip()
    create_audit_log(
        db=db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        action="workspace.updated",
        entity_type="workspace",
        entity_id=workspace.id,
        metadata={"old_name": old_name, "new_name": workspace.name},
    )

    db.commit()
    db.refresh(workspace)

    return attach_current_user_role(workspace, current_user, db)


def delete_workspace(
    workspace_id: int,
    current_user: models.User,
    db: Session,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        {schemas.WorkspaceRole.owner.value},
    )
    workspace = get_workspace_by_id(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o owner principal pode excluir o workspace.",
        )

    # Every table that belongs to a workspace has ON DELETE CASCADE on its
    # workspace_id FK (migration 0014), so a single delete removes all of it.
    db.delete(workspace)
    db.commit()

    return None


def list_workspace_members(
    workspace_id: int,
    current_user: models.User,
    db: Session,
    page: int = 1,
    limit: int = 20,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )

    query = (
        db.query(models.WorkspaceMember)
        .options(joinedload(models.WorkspaceMember.user))
        .filter(models.WorkspaceMember.workspace_id == workspace_id)
        .order_by(models.WorkspaceMember.id.asc())
    )

    return paginate_query(query, page, limit).all()


def get_member_by_id(
    workspace_id: int,
    member_id: int,
    db: Session,
):
    member = (
        db.query(models.WorkspaceMember)
        .filter(models.WorkspaceMember.workspace_id == workspace_id)
        .filter(models.WorkspaceMember.id == member_id)
        .first()
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro não encontrado.",
        )

    return member


def count_workspace_owners(workspace_id: int, db: Session):
    return (
        db.query(models.WorkspaceMember)
        .filter(models.WorkspaceMember.workspace_id == workspace_id)
        .filter(models.WorkspaceMember.role == schemas.WorkspaceRole.owner.value)
        .count()
    )


def is_workspace_owner_member(
    member: models.WorkspaceMember,
    workspace: models.Workspace,
):
    return (
        member.user_id == workspace.owner_id
        or member.role == schemas.WorkspaceRole.owner.value
    )


def ensure_admin_can_manage_member_role(
    current_member: models.WorkspaceMember,
    target_member: models.WorkspaceMember,
    new_role: str,
):
    if current_member.role != schemas.WorkspaceRole.admin.value:
        return

    if current_member.id == target_member.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin não pode alterar o próprio cargo.",
        )

    if target_member.role not in ADMIN_MEMBER_TARGET_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin só pode alterar membros employee ou viewer.",
        )

    if new_role not in ADMIN_MEMBER_TARGET_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin só pode alternar cargos entre employee e viewer.",
        )


def expire_pending_invites_for_email(
    workspace_id: int,
    email: str,
    current_user: models.User,
    db: Session,
):
    pending_invites = (
        db.query(models.WorkspaceInvite)
        .filter(models.WorkspaceInvite.workspace_id == workspace_id)
        .filter(models.WorkspaceInvite.email == email)
        .filter(models.WorkspaceInvite.status == schemas.InviteStatus.pending.value)
        .all()
    )

    for pending_invite in pending_invites:
        if not is_expired(pending_invite.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um convite pendente válido para este e-mail.",
            )

        expire_workspace_invite(pending_invite, current_user, db)

    if pending_invites:
        db.flush()


def expire_workspace_invite(
    invite: models.WorkspaceInvite,
    current_user: models.User,
    db: Session,
):
    invite.status = schemas.InviteStatus.expired.value
    release_workspace_invite_link_email(invite)
    create_audit_log(
        db=db,
        workspace_id=invite.workspace_id,
        user_id=current_user.id,
        action="invite.expired",
        entity_type="workspace_invite",
        entity_id=invite.id,
        metadata={"role": invite.role},
    )


def expire_workspace_invite_link(
    invite_link: models.WorkspaceInviteLink,
    current_user: models.User | None,
    db: Session,
):
    invite_link.status = schemas.InviteLinkStatus.expired.value
    create_audit_log(
        db=db,
        workspace_id=invite_link.workspace_id,
        user_id=current_user.id if current_user else None,
        action="invite_link.expired",
        entity_type="workspace_invite_link",
        entity_id=invite_link.id,
        metadata={"role": invite_link.role},
    )


def expire_stale_pending_invites(
    workspace_id: int,
    current_user: models.User,
    db: Session,
):
    pending_invites = (
        db.query(models.WorkspaceInvite)
        .filter(models.WorkspaceInvite.workspace_id == workspace_id)
        .filter(models.WorkspaceInvite.status == schemas.InviteStatus.pending.value)
        .all()
    )
    expired_any = False

    for invite in pending_invites:
        if is_expired(invite.expires_at):
            expire_workspace_invite(invite, current_user, db)
            expired_any = True

    if expired_any:
        db.commit()


def get_workspace_invite_link_email(workspace_id: int):
    return f"workspace-{workspace_id}@{INVITE_LINK_EMAIL_DOMAIN}"


def is_workspace_invite_link(invite: models.WorkspaceInvite):
    return invite.email.endswith(f"@{INVITE_LINK_EMAIL_DOMAIN}")


def release_workspace_invite_link_email(invite: models.WorkspaceInvite):
    if is_workspace_invite_link(invite):
        invite.email = f"{invite.status}-{invite.id}-{invite.email}"


def update_workspace_member(
    workspace_id: int,
    member_id: int,
    member_data: schemas.WorkspaceMemberUpdate,
    current_user: models.User,
    db: Session,
):
    current_member = require_workspace_role(
        workspace_id,
        current_user,
        db,
        MEMBER_ROLE_UPDATE_ROLES,
    )
    workspace = get_workspace_by_id(workspace_id, db)
    member = get_member_by_id(workspace_id, member_id, db)
    new_role = normalize_role(member_data.role)

    if is_workspace_owner_member(member, workspace):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível alterar o cargo de um owner.",
        )

    if new_role == schemas.WorkspaceRole.owner.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido atribuir o cargo owner por este endpoint.",
        )

    ensure_admin_can_manage_member_role(current_member, member, new_role)

    old_role = member.role
    member.role = new_role
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="member.role_updated",
        entity_type="workspace_member",
        entity_id=member.id,
        metadata={
            "member_user_id": member.user_id,
            "old_role": old_role,
            "new_role": member.role,
        },
    )

    db.commit()
    db.refresh(member)

    return member


def delete_workspace_member(
    workspace_id: int,
    member_id: int,
    current_user: models.User,
    db: Session,
):
    current_member = require_workspace_role(
        workspace_id,
        current_user,
        db,
        MEMBER_MANAGE_ROLES,
    )
    workspace = get_workspace_by_id(workspace_id, db)
    member = get_member_by_id(workspace_id, member_id, db)

    if is_workspace_owner_member(member, workspace):
        if count_workspace_owners(workspace_id, db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível remover o último owner do workspace.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover um owner por este endpoint.",
        )

    if (
        current_member.role == schemas.WorkspaceRole.admin.value
        and member.role not in ADMIN_MEMBER_TARGET_ROLES
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin só pode remover membros employee ou viewer.",
        )

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="member.removed",
        entity_type="workspace_member",
        entity_id=member.id,
        metadata={
            "member_user_id": member.user_id,
            "role": member.role,
        },
    )
    db.delete(member)
    db.commit()

    return None


def create_workspace_invite(
    workspace_id: int,
    invite_data: schemas.WorkspaceInviteCreate,
    current_user: models.User,
    db: Session,
):
    current_member = require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )
    role = normalize_role(invite_data.role)

    if (
        current_member.role == schemas.WorkspaceRole.admin.value
        and role not in {
            schemas.WorkspaceRole.employee.value,
            schemas.WorkspaceRole.viewer.value,
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin só pode convidar employee ou viewer.",
        )

    if role == schemas.WorkspaceRole.owner.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convites não podem criar novos owners.",
        )

    email = normalize_email(invite_data.email)
    existing_user = get_user_by_email(email, db)

    if existing_user and get_workspace_member(workspace_id, existing_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já é membro deste workspace.",
        )

    expire_pending_invites_for_email(workspace_id, email, current_user, db)

    invite = models.WorkspaceInvite(
        workspace_id=workspace_id,
        email=email,
        role=role,
        token=secrets.token_urlsafe(32),
        status=schemas.InviteStatus.pending.value,
        expires_at=aware_utc_now() + timedelta(days=7),
        created_by_user_id=current_user.id,
    )

    db.add(invite)
    try:
        db.flush()
        create_audit_log(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            action="invite.created",
            entity_type="workspace_invite",
            entity_id=invite.id,
            metadata={"role": invite.role},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um convite pendente válido para este e-mail.",
        )

    db.refresh(invite)

    return invite


def create_workspace_invite_link(
    workspace_id: int,
    invite_data: schemas.WorkspaceInviteLinkCreate,
    current_user: models.User,
    db: Session,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )
    role = normalize_role(invite_data.role)

    if role != schemas.WorkspaceRole.viewer.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Links de convite usam o cargo viewer por padrão.",
        )

    active_links = (
        db.query(models.WorkspaceInviteLink)
        .options(joinedload(models.WorkspaceInviteLink.acceptances))
        .filter(models.WorkspaceInviteLink.workspace_id == workspace_id)
        .filter(
            models.WorkspaceInviteLink.status
            == schemas.InviteLinkStatus.active.value
        )
        .order_by(models.WorkspaceInviteLink.created_at.desc())
        .all()
    )

    expired_any = False

    for active_link in active_links:
        if not is_expired(active_link.expires_at):
            return active_link

        expire_workspace_invite_link(active_link, current_user, db)
        expired_any = True

    if expired_any:
        db.flush()

    invite_link = models.WorkspaceInviteLink(
        workspace_id=workspace_id,
        role=schemas.WorkspaceRole.viewer.value,
        token=secrets.token_urlsafe(32),
        status=schemas.InviteLinkStatus.active.value,
        expires_at=aware_utc_now() + timedelta(days=7),
        created_by_user_id=current_user.id,
    )

    db.add(invite_link)
    db.flush()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="invite_link.created",
        entity_type="workspace_invite_link",
        entity_id=invite_link.id,
        metadata={"role": invite_link.role},
    )
    db.commit()
    db.refresh(invite_link)

    return invite_link


def list_workspace_invite_links(
    workspace_id: int,
    current_user: models.User,
    db: Session,
    page: int = 1,
    limit: int = 20,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )
    invite_links = (
        paginate_query(
            db.query(models.WorkspaceInviteLink)
            .options(joinedload(models.WorkspaceInviteLink.acceptances))
            .filter(models.WorkspaceInviteLink.workspace_id == workspace_id)
            .order_by(models.WorkspaceInviteLink.created_at.desc()),
            page,
            limit,
        )
        .all()
    )
    expired_any = False

    for invite_link in invite_links:
        if (
            invite_link.status == schemas.InviteLinkStatus.active.value
            and is_expired(invite_link.expires_at)
        ):
            expire_workspace_invite_link(invite_link, current_user, db)
            expired_any = True

    if expired_any:
        db.commit()

    return invite_links


def list_workspace_invites(
    workspace_id: int,
    current_user: models.User,
    db: Session,
    page: int = 1,
    limit: int = 20,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )
    expire_stale_pending_invites(workspace_id, current_user, db)

    query = (
        db.query(models.WorkspaceInvite)
        .filter(models.WorkspaceInvite.workspace_id == workspace_id)
        .filter(
            ~models.WorkspaceInvite.email.like(
                f"%@{INVITE_LINK_EMAIL_DOMAIN}"
            )
        )
        .order_by(models.WorkspaceInvite.created_at.desc())
    )

    return paginate_query(query, page, limit).all()


def get_workspace_team(
    workspace_id: int,
    current_user: models.User,
    db: Session,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )
    expire_stale_pending_invites(workspace_id, current_user, db)

    members = (
        db.query(models.WorkspaceMember)
        .options(joinedload(models.WorkspaceMember.user))
        .filter(models.WorkspaceMember.workspace_id == workspace_id)
        .order_by(models.WorkspaceMember.id.asc())
        .limit(100)
        .all()
    )
    pending_invites = (
        db.query(models.WorkspaceInvite)
        .filter(models.WorkspaceInvite.workspace_id == workspace_id)
        .filter(models.WorkspaceInvite.status == schemas.InviteStatus.pending.value)
        .filter(
            ~models.WorkspaceInvite.email.like(
                f"%@{INVITE_LINK_EMAIL_DOMAIN}"
            )
        )
        .order_by(models.WorkspaceInvite.created_at.desc())
        .limit(100)
        .all()
    )

    return {
        "members": members,
        "pending_invites": pending_invites,
    }


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


def accept_workspace_invite(
    token: str,
    current_user: models.User,
    db: Session,
):
    invite = (
        db.query(models.WorkspaceInvite)
        .filter(models.WorkspaceInvite.token == token)
        .first()
    )

    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado.",
        )

    if invite.status != schemas.InviteStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convite não está pendente.",
        )

    if is_expired(invite.expires_at):
        expire_workspace_invite(invite, current_user, db)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convite expirado.",
        )

    is_invite_link = is_workspace_invite_link(invite)

    if (
        not is_invite_link
        and normalize_email(current_user.email) != normalize_email(invite.email)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O e-mail do usuário não corresponde ao convite.",
        )

    if invite.role == schemas.WorkspaceRole.owner.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convites não podem criar novos owners.",
        )

    member = get_workspace_member(invite.workspace_id, current_user.id, db)

    if member is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já é membro deste workspace.",
        )

    member = models.WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=current_user.id,
        role=invite.role,
    )
    db.add(member)
    db.flush()

    invite.status = schemas.InviteStatus.accepted.value
    invite.accepted_by_user_id = current_user.id
    invite.accepted_at = aware_utc_now()
    release_workspace_invite_link_email(invite)
    create_audit_log(
        db=db,
        workspace_id=invite.workspace_id,
        user_id=current_user.id,
        action="invite.accepted",
        entity_type="workspace_invite",
        entity_id=invite.id,
        metadata={"role": invite.role},
    )

    db.commit()
    db.refresh(member)

    return member


def accept_workspace_invite_link(
    token: str,
    current_user: models.User,
    db: Session,
):
    invite_link = (
        db.query(models.WorkspaceInviteLink)
        .options(joinedload(models.WorkspaceInviteLink.acceptances))
        .filter(models.WorkspaceInviteLink.token == token)
        .first()
    )

    if invite_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link de convite não encontrado.",
        )

    if invite_link.status == schemas.InviteLinkStatus.revoked.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de convite revogado.",
        )

    if invite_link.status == schemas.InviteLinkStatus.expired.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de convite expirado.",
        )

    if is_expired(invite_link.expires_at):
        expire_workspace_invite_link(invite_link, current_user, db)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de convite expirado.",
        )

    member = get_workspace_member(invite_link.workspace_id, current_user.id, db)
    existing_acceptance = (
        db.query(models.WorkspaceInviteLinkAcceptance)
        .filter(
            models.WorkspaceInviteLinkAcceptance.invite_link_id
            == invite_link.id
        )
        .filter(models.WorkspaceInviteLinkAcceptance.user_id == current_user.id)
        .first()
    )

    if member is not None and existing_acceptance is not None:
        return member

    if member is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já é membro deste workspace.",
        )

    member = models.WorkspaceMember(
        workspace_id=invite_link.workspace_id,
        user_id=current_user.id,
        role=schemas.WorkspaceRole.viewer.value,
    )
    db.add(member)
    db.flush()

    db.add(
        models.WorkspaceInviteLinkAcceptance(
            invite_link_id=invite_link.id,
            user_id=current_user.id,
        )
    )
    create_audit_log(
        db=db,
        workspace_id=invite_link.workspace_id,
        user_id=current_user.id,
        action="invite_link.accepted",
        entity_type="workspace_invite_link",
        entity_id=invite_link.id,
        metadata={
            "invite_link_id": invite_link.id,
            "role": schemas.WorkspaceRole.viewer.value,
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        member = get_workspace_member(invite_link.workspace_id, current_user.id, db)

        if member is not None:
            return member

        raise

    db.refresh(member)

    return member


def revoke_workspace_invite_link(
    workspace_id: int,
    link_id: int,
    current_user: models.User,
    db: Session,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )
    invite_link = (
        db.query(models.WorkspaceInviteLink)
        .options(joinedload(models.WorkspaceInviteLink.acceptances))
        .filter(models.WorkspaceInviteLink.workspace_id == workspace_id)
        .filter(models.WorkspaceInviteLink.id == link_id)
        .first()
    )

    if invite_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link de convite não encontrado.",
        )

    if (
        invite_link.status == schemas.InviteLinkStatus.active.value
        and is_expired(invite_link.expires_at)
    ):
        expire_workspace_invite_link(invite_link, current_user, db)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de convite expirado.",
        )

    if invite_link.status != schemas.InviteLinkStatus.active.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Somente links ativos podem ser revogados.",
        )

    invite_link.status = schemas.InviteLinkStatus.revoked.value
    invite_link.revoked_at = aware_utc_now()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="invite_link.revoked",
        entity_type="workspace_invite_link",
        entity_id=invite_link.id,
        metadata={
            "invite_link_id": invite_link.id,
            "role": invite_link.role,
        },
    )

    db.commit()
    db.refresh(invite_link)

    return invite_link


def revoke_workspace_invite(
    workspace_id: int,
    invite_id: int,
    current_user: models.User,
    db: Session,
):
    current_member = require_workspace_role(
        workspace_id,
        current_user,
        db,
        INVITE_MANAGE_ROLES,
    )
    invite = (
        db.query(models.WorkspaceInvite)
        .filter(models.WorkspaceInvite.workspace_id == workspace_id)
        .filter(models.WorkspaceInvite.id == invite_id)
        .first()
    )

    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado.",
        )

    if (
        current_member.role == schemas.WorkspaceRole.admin.value
        and invite.role not in ADMIN_MEMBER_TARGET_ROLES
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin só pode revogar convites de employee ou viewer.",
        )

    if invite.status == schemas.InviteStatus.pending.value and is_expired(
        invite.expires_at,
    ):
        expire_workspace_invite(invite, current_user, db)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convite expirado.",
        )

    if invite.status != schemas.InviteStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Somente convites pendentes podem ser revogados.",
        )

    invite.status = schemas.InviteStatus.revoked.value
    release_workspace_invite_link_email(invite)
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="invite.revoked",
        entity_type="workspace_invite",
        entity_id=invite.id,
        metadata={"role": invite.role},
    )

    db.commit()
    db.refresh(invite)

    return invite


def get_product_by_id(
    product_id: int,
    db: Session,
    workspace_id: int | None = None,
    include_deleted: bool = False,
    for_update: bool = False,
):
    query = db.query(models.Product).filter(models.Product.id == product_id)

    if workspace_id is None:
        query = query.filter(models.Product.workspace_id.is_(None))
    else:
        query = query.filter(models.Product.workspace_id == workspace_id)

    if not include_deleted:
        query = query.filter(models.Product.is_active.is_(True))

    if for_update and db.bind is not None and db.bind.dialect.name != "sqlite":
        query = query.with_for_update()

    product = query.first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    return product


def get_product_by_name(
    name: str,
    workspace_id: int,
    db: Session,
    only_active: bool = False,
):
    query = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.name == name)
    )

    if only_active:
        query = query.filter(models.Product.is_active.is_(True))

    return query.first()


def resolve_category_id(name: str, workspace_id: int, db: Session):
    """Best-effort link of a product's category name to its Category row.

    Returns None when no active category with that name exists in the
    workspace (arbitrary strings from non-UI clients stay unlinked).
    """
    category = get_category_by_name(name, db, workspace_id, only_active=True)

    return category.id if category else None


def create_product(
    product_data: schemas.ProductCreate,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    name = product_data.name.strip()
    existing_product = get_product_by_name(
        name,
        workspace_id,
        db,
        only_active=True,
    )

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ACTIVE_PRODUCT_NAME_EXISTS,
        )

    category_name = product_data.category.strip()
    new_product = models.Product(
        workspace_id=workspace_id,
        name=name,
        category=category_name,
        category_id=resolve_category_id(category_name, workspace_id, db),
        quantity=product_data.quantity,
        minimum_quantity=product_data.minimum_quantity,
    )

    db.add(new_product)
    db.flush()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="product.created",
        entity_type="product",
        entity_id=new_product.id,
        metadata={
            "name": new_product.name,
            "category": new_product.category,
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ACTIVE_PRODUCT_NAME_EXISTS,
        )

    db.refresh(new_product)

    return new_product


def list_products(
    db: Session,
    workspace_id: int,
    category: str | None = None,
    search: str | None = None,
    product_status: schemas.ProductStatus | str = schemas.ProductStatus.active,
    page: int = 1,
    limit: int = 20,
):
    query = db.query(models.Product).filter(
        models.Product.workspace_id == workspace_id
    )
    status_value = normalize_product_status(product_status)

    if status_value == schemas.ProductStatus.active.value:
        query = query.filter(models.Product.is_active.is_(True))
    elif status_value == schemas.ProductStatus.deleted.value:
        query = query.filter(models.Product.is_active.is_(False))
    elif status_value != schemas.ProductStatus.all.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status de produto inválido.",
        )

    if category:
        query = query.filter(models.Product.category.ilike(f"%{category}%"))

    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))

    query = query.order_by(models.Product.name.asc())

    return paginate_query(query, page, limit).all()


def list_low_stock_products(
    db: Session,
    workspace_id: int,
    page: int = 1,
    limit: int = 20,
):
    query = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .filter(models.Product.quantity > 0)
        .filter(models.Product.quantity < models.Product.minimum_quantity)
        .order_by(models.Product.quantity.asc())
    )

    return paginate_query(query, page, limit).all()


def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    product = get_product_by_id(product_id, db, workspace_id)

    update_data = product_data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = update_data["name"].strip()
        existing_product = get_product_by_name(
            new_name,
            workspace_id,
            db,
            only_active=True,
        )

        if existing_product and existing_product.id != product.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
            )

        update_data["name"] = new_name

    if "category" in update_data:
        update_data["category"] = update_data["category"].strip()
        product.category_id = resolve_category_id(
            update_data["category"],
            workspace_id,
            db,
        )

    for field, value in update_data.items():
        setattr(product, field, value)

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="product.updated",
        entity_type="product",
        entity_id=product.id,
        metadata={
            "name": product.name,
            "fields": sorted(update_data.keys()),
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
        )

    db.refresh(product)

    return product


def delete_product(
    product_id: int,
    db: Session,
    workspace_id: int,
    deleted_by_user_id: int,
):
    product = get_product_by_id(
        product_id,
        db,
        workspace_id,
        include_deleted=True,
    )

    if not product.is_active:
        return product

    product.is_active = False
    product.deleted_at = aware_utc_now()
    product.deleted_by_user_id = deleted_by_user_id
    product.deleted_by_category_id = None
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=deleted_by_user_id,
        action="product.deleted",
        entity_type="product",
        entity_id=product.id,
        metadata={"name": product.name},
    )

    db.commit()
    db.refresh(product)

    return product


def restore_product(
    product_id: int,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    product = get_product_by_id(
        product_id,
        db,
        workspace_id,
        include_deleted=True,
    )

    if product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O produto já está ativo.",
        )

    if product.deleted_by_category_id is not None:
        deleted_category = get_category_by_id(
            product.deleted_by_category_id,
            db,
            workspace_id,
            include_deleted=True,
        )

        if not deleted_category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Restaure a categoria antes de restaurar este produto.",
            )

    existing_product = get_product_by_name(
        product.name,
        workspace_id,
        db,
        only_active=True,
    )

    if existing_product and existing_product.id != product.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
        )

    product.is_active = True
    product.deleted_at = None
    product.deleted_by_user_id = None
    product.deleted_by_category_id = None
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="product.restored",
        entity_type="product",
        entity_id=product.id,
        metadata={"name": product.name},
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS,
        )

    db.refresh(product)

    return product


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível movimentar estoque de um produto inativo.",
        )

    replenishment_request = None

    if movement_data.replenishment_request_id is not None:
        replenishment_request = get_replenishment_request_by_id(
            workspace_id,
            movement_data.replenishment_request_id,
            db,
        )

        if replenishment_request.product_id != product.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A necessidade de reposição não pertence a este produto.",
            )

        if movement_data.movement_type != schemas.StockMovementType.entrada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uma reposição só pode ser vinculada a uma entrada.",
            )

        if (
            replenishment_request.status
            != schemas.ReplenishmentStatus.completed.value
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A necessidade não está pronta para estocar.",
            )

    quantity_before = product.quantity

    if (
        movement_data.movement_type != schemas.StockMovementType.ajuste
        and movement_data.quantity <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A quantidade da movimentação precisa ser maior que zero.",
        )

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


def get_replenishment_request_by_id(
    workspace_id: int,
    request_id: int,
    db: Session,
):
    replenishment_request = (
        db.query(models.ReplenishmentRequest)
        .options(
            joinedload(models.ReplenishmentRequest.product),
            joinedload(models.ReplenishmentRequest.created_by_user),
            joinedload(models.ReplenishmentRequest.assigned_to_user),
            joinedload(models.ReplenishmentRequest.assignees).joinedload(
                models.ReplenishmentAssignee.user
            ),
            joinedload(models.ReplenishmentRequest.workspace).joinedload(
                models.Workspace.members
            ),
        )
        .filter(models.ReplenishmentRequest.workspace_id == workspace_id)
        .filter(models.ReplenishmentRequest.id == request_id)
        .first()
    )

    if replenishment_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Necessidade de reposição não encontrada.",
        )

    return replenishment_request


def validate_replenishment_assignee(
    workspace_id: int,
    assigned_to_user_id: int | None,
    db: Session,
):
    if assigned_to_user_id is None:
        return

    if get_workspace_member(workspace_id, assigned_to_user_id, db) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O responsável deve ser membro deste workspace.",
        )


def replenishment_metadata(replenishment_request):
    return {
        "product_id": replenishment_request.product_id,
        "product_name": replenishment_request.product.name,
        "type": replenishment_request.type,
        "status": replenishment_request.status,
        "quantity_needed": replenishment_request.quantity_needed,
    }


def is_active_replenishment_unique_violation(error: IntegrityError):
    original_error = getattr(error, "orig", None)
    diagnostic = getattr(original_error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    if constraint_name == ACTIVE_REPLENISHMENT_INDEX_NAME:
        return True

    error_message = str(original_error or error)

    if ACTIVE_REPLENISHMENT_INDEX_NAME in error_message:
        return True

    normalized_message = error_message.lower()

    return (
        "unique constraint failed" in normalized_message
        and "replenishment_requests.workspace_id" in normalized_message
        and "replenishment_requests.product_id" in normalized_message
    )


def create_replenishment_request(
    workspace_id: int,
    request_data: schemas.ReplenishmentRequestCreate,
    current_user: models.User,
    db: Session,
):
    product = get_product_by_id(
        request_data.product_id,
        db,
        workspace_id,
    )
    validate_replenishment_assignee(
        workspace_id,
        request_data.assigned_to_user_id,
        db,
    )

    active_request = (
        db.query(models.ReplenishmentRequest.id)
        .filter(models.ReplenishmentRequest.workspace_id == workspace_id)
        .filter(models.ReplenishmentRequest.product_id == product.id)
        .filter(
            models.ReplenishmentRequest.status.in_(
                ACTIVE_REPLENISHMENT_STATUSES
            )
        )
        .first()
    )

    if active_request is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ACTIVE_REPLENISHMENT_EXISTS,
        )

    replenishment_request = models.ReplenishmentRequest(
        workspace_id=workspace_id,
        product_id=product.id,
        created_by_user_id=current_user.id,
        assigned_to_user_id=request_data.assigned_to_user_id,
        type=request_data.type.value,
        status=schemas.ReplenishmentStatus.open.value,
        quantity_needed=request_data.quantity_needed,
        notes=request_data.notes,
    )
    request_id = None

    try:
        db.add(replenishment_request)
        db.flush()
        request_id = replenishment_request.id
        replenishment_request.product = product

        if request_data.assigned_to_user_id is not None:
            db.add(
                models.ReplenishmentAssignee(
                    replenishment_id=replenishment_request.id,
                    user_id=request_data.assigned_to_user_id,
                    assigned_by_user_id=current_user.id,
                )
            )

        create_audit_log(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            action="replenishment.created",
            entity_type="replenishment_request",
            entity_id=replenishment_request.id,
            metadata=replenishment_metadata(replenishment_request),
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()

        if is_active_replenishment_unique_violation(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ACTIVE_REPLENISHMENT_EXISTS,
            ) from error

        raise

    return get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )


def list_replenishment_requests(
    workspace_id: int,
    db: Session,
    request_status: schemas.ReplenishmentStatusFilter | str | None = None,
    page: int = 1,
    limit: int = 20,
):
    query = (
        db.query(models.ReplenishmentRequest)
        .options(
            joinedload(models.ReplenishmentRequest.product),
            joinedload(models.ReplenishmentRequest.created_by_user),
            joinedload(models.ReplenishmentRequest.assigned_to_user),
            joinedload(models.ReplenishmentRequest.assignees).joinedload(
                models.ReplenishmentAssignee.user
            ),
            joinedload(models.ReplenishmentRequest.workspace).joinedload(
                models.Workspace.members
            ),
        )
        .filter(models.ReplenishmentRequest.workspace_id == workspace_id)
    )

    if request_status is None:
        query = query.filter(
            models.ReplenishmentRequest.status.in_(
                [
                    schemas.ReplenishmentStatus.open.value,
                    schemas.ReplenishmentStatus.in_progress.value,
                ]
            )
        )
    else:
        status_value = (
            request_status.value
            if hasattr(request_status, "value")
            else str(request_status)
        )

        if status_value != schemas.ReplenishmentStatusFilter.all.value:
            query = query.filter(
                models.ReplenishmentRequest.status == status_value
            )

    query = query.order_by(models.ReplenishmentRequest.created_at.desc())

    return paginate_query(query, page, limit).all()


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


def update_replenishment_request(
    workspace_id: int,
    request_id: int,
    request_data: schemas.ReplenishmentRequestUpdate,
    current_user: models.User,
    db: Session,
):
    member = require_workspace_role(
        workspace_id,
        current_user,
        db,
        REPLENISHMENT_UPDATE_ROLES,
    )
    replenishment_request = get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )
    update_data = request_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe ao menos um campo para atualizar.",
        )

    if member.role == schemas.WorkspaceRole.employee.value:
        if set(update_data) != {"status"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee pode atualizar apenas o status.",
            )

        allowed_statuses = {
            schemas.ReplenishmentStatus.in_progress,
            schemas.ReplenishmentStatus.completed,
        }

        if update_data["status"] not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Employee pode marcar a necessidade como em andamento "
                    "ou concluída."
                ),
            )

    for required_field in ("type", "status", "quantity_needed"):
        if required_field in update_data and update_data[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O campo {required_field} não pode ser nulo.",
            )

    if "assigned_to_user_id" in update_data:
        ensure_replenishment_accepts_assignees(replenishment_request)
        validate_replenishment_assignee(
            workspace_id,
            update_data["assigned_to_user_id"],
            db,
        )

        if update_data["assigned_to_user_id"] is not None:
            existing_assignee = (
                db.query(models.ReplenishmentAssignee)
                .filter(
                    models.ReplenishmentAssignee.replenishment_id == request_id
                )
                .filter(
                    models.ReplenishmentAssignee.user_id
                    == update_data["assigned_to_user_id"]
                )
                .first()
            )

            if existing_assignee is None:
                db.add(
                    models.ReplenishmentAssignee(
                        replenishment_id=request_id,
                        user_id=update_data["assigned_to_user_id"],
                        assigned_by_user_id=current_user.id,
                    )
                )

    old_status = replenishment_request.status

    if (
        update_data.get("status") == schemas.ReplenishmentStatus.stocked
        and old_status != schemas.ReplenishmentStatus.completed.value
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A necessidade precisa estar pronta para estocar antes de ser "
                "marcada como estocada."
            ),
        )

    for field, value in update_data.items():
        if hasattr(value, "value"):
            value = value.value

        setattr(replenishment_request, field, value)

    if (
        replenishment_request.status == schemas.ReplenishmentStatus.completed.value
        and old_status != schemas.ReplenishmentStatus.completed.value
    ):
        replenishment_request.completed_at = aware_utc_now()
    elif (
        old_status == schemas.ReplenishmentStatus.completed.value
        and replenishment_request.status
        not in {
            schemas.ReplenishmentStatus.completed.value,
            schemas.ReplenishmentStatus.stocked.value,
        }
    ):
        replenishment_request.completed_at = None

    audit_action = "replenishment.updated"

    if (
        old_status != replenishment_request.status
        and replenishment_request.status
        == schemas.ReplenishmentStatus.completed.value
    ):
        audit_action = "replenishment.completed"
    elif (
        old_status != replenishment_request.status
        and replenishment_request.status
        == schemas.ReplenishmentStatus.stocked.value
    ):
        audit_action = "replenishment.stocked"
    elif (
        old_status != replenishment_request.status
        and replenishment_request.status
        == schemas.ReplenishmentStatus.canceled.value
    ):
        audit_action = "replenishment.canceled"

    metadata = replenishment_metadata(replenishment_request)
    metadata["fields"] = sorted(update_data.keys())
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action=audit_action,
        entity_type="replenishment_request",
        entity_id=replenishment_request.id,
        metadata=metadata,
    )
    db.commit()

    return get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )


def ensure_replenishment_accepts_assignees(replenishment_request):
    if replenishment_request.status in {
        schemas.ReplenishmentStatus.completed.value,
        schemas.ReplenishmentStatus.stocked.value,
        schemas.ReplenishmentStatus.canceled.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não é possível alterar responsáveis de uma necessidade "
                "concluída, estocada ou cancelada."
            ),
        )


def assign_replenishment_user(
    workspace_id: int,
    request_id: int,
    user_id: int,
    assigned_by_user_id: int,
    db: Session,
):
    replenishment_request = get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )
    ensure_replenishment_accepts_assignees(replenishment_request)
    validate_replenishment_assignee(workspace_id, user_id, db)
    existing_assignee = (
        db.query(models.ReplenishmentAssignee)
        .filter(models.ReplenishmentAssignee.replenishment_id == request_id)
        .filter(models.ReplenishmentAssignee.user_id == user_id)
        .first()
    )

    if existing_assignee is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuário já está atribuído à necessidade.",
        )

    assignment = models.ReplenishmentAssignee(
        replenishment_id=request_id,
        user_id=user_id,
        assigned_by_user_id=assigned_by_user_id,
    )
    db.add(assignment)

    if replenishment_request.assigned_to_user_id is None:
        replenishment_request.assigned_to_user_id = user_id

    replenishment_request.updated_at = aware_utc_now()
    metadata = replenishment_metadata(replenishment_request)
    metadata["assignee_user_id"] = user_id
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=assigned_by_user_id,
        action="replenishment.assignee_added",
        entity_type="replenishment_request",
        entity_id=request_id,
        metadata=metadata,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuário já está atribuído à necessidade.",
        )

    return get_replenishment_request_by_id(workspace_id, request_id, db)


def remove_replenishment_user(
    workspace_id: int,
    request_id: int,
    user_id: int,
    removed_by_user_id: int,
    db: Session,
):
    replenishment_request = get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )
    ensure_replenishment_accepts_assignees(replenishment_request)
    assignment = (
        db.query(models.ReplenishmentAssignee)
        .filter(models.ReplenishmentAssignee.replenishment_id == request_id)
        .filter(models.ReplenishmentAssignee.user_id == user_id)
        .first()
    )

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este usuário não está atribuído à necessidade.",
        )

    db.delete(assignment)

    if replenishment_request.assigned_to_user_id == user_id:
        next_assignee = (
            db.query(models.ReplenishmentAssignee)
            .filter(models.ReplenishmentAssignee.replenishment_id == request_id)
            .filter(models.ReplenishmentAssignee.user_id != user_id)
            .order_by(models.ReplenishmentAssignee.created_at.asc())
            .first()
        )
        replenishment_request.assigned_to_user_id = (
            next_assignee.user_id if next_assignee else None
        )

    replenishment_request.updated_at = aware_utc_now()
    metadata = replenishment_metadata(replenishment_request)
    metadata["assignee_user_id"] = user_id
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=removed_by_user_id,
        action="replenishment.assignee_removed",
        entity_type="replenishment_request",
        entity_id=request_id,
        metadata=metadata,
    )
    db.commit()

    return get_replenishment_request_by_id(workspace_id, request_id, db)


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma categoria com esse nome neste workspace.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não foi possível criar a categoria com esse nome. "
                "No SQLite atual ainda pode existir uma constraint global antiga."
            ),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status de categoria inválido.",
        )

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com esse nome neste workspace.",
            )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não foi possível atualizar a categoria com esse nome. "
                "No SQLite atual ainda pode existir uma constraint global antiga."
            ),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_CATEGORY_NAME_EXISTS,
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ANOTHER_ACTIVE_CATEGORY_NAME_EXISTS,
        )

    db.refresh(category)

    return {
        "category": category,
        "restored_products_count": restored_products_count,
        "skipped_products_count": skipped_products_count,
    }


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
