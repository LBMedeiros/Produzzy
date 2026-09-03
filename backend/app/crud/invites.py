"""crud.invites — split from the former monolithic crud.py."""
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
from app.crud.users import get_user_by_email

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
            raise ValidationError("Já existe um convite pendente válido para este e-mail.")

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
        raise PermissionDenied("Admin só pode convidar employee ou viewer.")

    if role == schemas.WorkspaceRole.owner.value:
        raise ValidationError("Convites não podem criar novos owners.")

    email = normalize_email(invite_data.email)
    existing_user = get_user_by_email(email, db)

    if existing_user and get_workspace_member(workspace_id, existing_user.id, db):
        raise ValidationError("Usuário já é membro deste workspace.")

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
        raise ValidationError("Já existe um convite pendente válido para este e-mail.")

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
        raise ValidationError("Links de convite usam o cargo viewer por padrão.")

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
        raise NotFound("Convite não encontrado.")

    if invite.status != schemas.InviteStatus.pending.value:
        raise ValidationError("Convite não está pendente.")

    if is_expired(invite.expires_at):
        expire_workspace_invite(invite, current_user, db)
        db.commit()
        raise ValidationError("Convite expirado.")

    is_invite_link = is_workspace_invite_link(invite)

    if (
        not is_invite_link
        and normalize_email(current_user.email) != normalize_email(invite.email)
    ):
        raise PermissionDenied("O e-mail do usuário não corresponde ao convite.")

    if invite.role == schemas.WorkspaceRole.owner.value:
        raise ValidationError("Convites não podem criar novos owners.")

    member = get_workspace_member(invite.workspace_id, current_user.id, db)

    if member is not None:
        raise ValidationError("Usuário já é membro deste workspace.")

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
        raise NotFound("Link de convite não encontrado.")

    if invite_link.status == schemas.InviteLinkStatus.revoked.value:
        raise ValidationError("Link de convite revogado.")

    if invite_link.status == schemas.InviteLinkStatus.expired.value:
        raise ValidationError("Link de convite expirado.")

    if is_expired(invite_link.expires_at):
        expire_workspace_invite_link(invite_link, current_user, db)
        db.commit()
        raise ValidationError("Link de convite expirado.")

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
        raise ValidationError("Usuário já é membro deste workspace.")

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
        raise NotFound("Link de convite não encontrado.")

    if (
        invite_link.status == schemas.InviteLinkStatus.active.value
        and is_expired(invite_link.expires_at)
    ):
        expire_workspace_invite_link(invite_link, current_user, db)
        db.commit()
        raise ValidationError("Link de convite expirado.")

    if invite_link.status != schemas.InviteLinkStatus.active.value:
        raise ValidationError("Somente links ativos podem ser revogados.")

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
        raise NotFound("Convite não encontrado.")

    if (
        current_member.role == schemas.WorkspaceRole.admin.value
        and invite.role not in ADMIN_MEMBER_TARGET_ROLES
    ):
        raise PermissionDenied("Admin só pode revogar convites de employee ou viewer.")

    if invite.status == schemas.InviteStatus.pending.value and is_expired(
        invite.expires_at,
    ):
        expire_workspace_invite(invite, current_user, db)
        db.commit()
        raise ValidationError("Convite expirado.")

    if invite.status != schemas.InviteStatus.pending.value:
        raise ValidationError("Somente convites pendentes podem ser revogados.")

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
