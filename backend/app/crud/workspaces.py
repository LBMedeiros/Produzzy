"""crud.workspaces — split from the former monolithic crud.py."""
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
from app.crud.products import list_product_image_ids

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
    workspace.current_user_title = membership.title if membership else None

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
    titles_by_workspace_id = {
        membership.workspace_id: membership.title for membership in memberships
    }
    member_counts_by_workspace_id = dict(
        db.query(
            models.WorkspaceMember.workspace_id,
            func.count(models.WorkspaceMember.id),
        )
        .filter(models.WorkspaceMember.workspace_id.in_(workspace_ids))
        .group_by(models.WorkspaceMember.workspace_id)
        .all()
    )

    for workspace in workspaces:
        workspace.current_user_role = roles_by_workspace_id.get(workspace.id)
        workspace.current_user_title = titles_by_workspace_id.get(workspace.id)
        workspace.member_count = member_counts_by_workspace_id.get(workspace.id, 0)

    return workspaces

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
        raise PermissionDenied("Apenas o owner principal pode excluir o workspace.")

    # Product photos live on Cloudinary; return their ids so the router can
    # remove the files once the rows are gone.
    product_image_ids = list_product_image_ids([workspace_id], db)

    # Every table that belongs to a workspace has ON DELETE CASCADE on its
    # workspace_id FK (migration 0014), so a single delete removes all of it.
    db.delete(workspace)
    db.commit()

    return product_image_ids

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
        raise NotFound("Membro não encontrado.")

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
        raise PermissionDenied("Admin não pode alterar a própria permissão.")

    if target_member.role not in ADMIN_MEMBER_TARGET_ROLES:
        raise PermissionDenied("Admin só pode alterar Funcionários e Visualizadores.")

    if new_role not in ADMIN_MEMBER_TARGET_ROLES:
        raise PermissionDenied("Admin só pode dar a permissão de Funcionário ou Visualizador.")

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
        raise ValidationError("Não é possível alterar a permissão do dono.")

    if new_role == schemas.WorkspaceRole.owner.value:
        raise ValidationError("Não é possível tornar alguém dono por aqui.")

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

def update_workspace_member_title(
    workspace_id: int,
    member_id: int,
    title,
    current_user: models.User,
    db: Session,
):
    current_member = require_workspace_role(
        workspace_id,
        current_user,
        db,
        MEMBER_TITLE_MANAGE_ROLES,
    )
    member = get_member_by_id(workspace_id, member_id, db)

    # Admins set titles only for the people whose permission they manage.
    if (
        current_member.role == schemas.WorkspaceRole.admin.value
        and member.role not in ADMIN_MEMBER_TARGET_ROLES
    ):
        raise PermissionDenied(
            "Admin só pode definir o cargo de Funcionários e Visualizadores."
        )

    normalized_title = normalize_member_title(title)

    old_title = member.title
    member.title = normalized_title
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="member.title_updated",
        entity_type="workspace_member",
        entity_id=member.id,
        metadata={
            "member_user_id": member.user_id,
            "old_title": old_title,
            "new_title": member.title,
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
            raise ValidationError("Não é possível remover o último owner do workspace.")

        raise ValidationError("Não é possível remover um owner por este endpoint.")

    if (
        current_member.role == schemas.WorkspaceRole.admin.value
        and member.role not in ADMIN_MEMBER_TARGET_ROLES
    ):
        raise PermissionDenied("Admin só pode remover Funcionários e Visualizadores.")

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
