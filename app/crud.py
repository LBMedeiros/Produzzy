import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.services.security_service import get_password_hash, verify_password


READ_ROLES = {"owner", "admin", "employee", "viewer"}
PRODUCT_WRITE_ROLES = {"owner", "admin"}
CATEGORY_WRITE_ROLES = {"owner", "admin"}
STOCK_WRITE_ROLES = {"owner", "admin", "employee"}
MEMBER_MANAGE_ROLES = {"owner"}
INVITE_MANAGE_ROLES = {"owner", "admin"}
AUDIT_LOG_READ_ROLES = {"owner", "admin"}
ACTIVE_PRODUCT_NAME_EXISTS = (
    "An active product with this name already exists in this workspace."
)
ANOTHER_ACTIVE_PRODUCT_NAME_EXISTS = (
    "Another active product with this name already exists in this workspace."
)


def normalize_email(email: str):
    return email.strip().lower()


def get_user_by_email(email: str, db: Session):
    return (
        db.query(models.User)
        .filter(models.User.email == normalize_email(email))
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
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def authenticate_user(login_data: schemas.UserLogin, db: Session):
    user = get_user_by_email(login_data.email, db)

    if not user or not verify_password(
        login_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo.",
        )

    return user


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


def normalize_product_status(product_status):
    if hasattr(product_status, "value"):
        return product_status.value

    return str(product_status)


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

    return paginate_query(query, page, limit).all()


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

    return workspace


def get_workspace_for_user(
    workspace_id: int,
    current_user: models.User,
    db: Session,
):
    require_workspace_member(workspace_id, current_user, db)

    return get_workspace_by_id(workspace_id, db)


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

    return workspace


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


def update_workspace_member(
    workspace_id: int,
    member_id: int,
    member_data: schemas.WorkspaceMemberUpdate,
    current_user: models.User,
    db: Session,
):
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        MEMBER_MANAGE_ROLES,
    )
    member = get_member_by_id(workspace_id, member_id, db)
    new_role = normalize_role(member_data.role)

    if (
        member.role == schemas.WorkspaceRole.owner.value
        and new_role != schemas.WorkspaceRole.owner.value
        and count_workspace_owners(workspace_id, db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover o último owner do workspace.",
        )

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
    require_workspace_role(
        workspace_id,
        current_user,
        db,
        MEMBER_MANAGE_ROLES,
    )
    member = get_member_by_id(workspace_id, member_id, db)

    if (
        member.role == schemas.WorkspaceRole.owner.value
        and count_workspace_owners(workspace_id, db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover o último owner do workspace.",
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
    db.refresh(invite)

    return invite


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

    query = (
        db.query(models.WorkspaceInvite)
        .filter(models.WorkspaceInvite.workspace_id == workspace_id)
        .order_by(models.WorkspaceInvite.created_at.desc())
    )

    return paginate_query(query, page, limit).all()


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
        invite.status = schemas.InviteStatus.expired.value
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Convite expirado.",
        )

    if normalize_email(current_user.email) != normalize_email(invite.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O e-mail do usuário não corresponde ao convite.",
        )

    member = get_workspace_member(invite.workspace_id, current_user.id, db)

    if member is None:
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


def revoke_workspace_invite(
    workspace_id: int,
    invite_id: int,
    current_user: models.User,
    db: Session,
):
    require_workspace_role(
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

    if invite.status != schemas.InviteStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Somente convites pendentes podem ser revogados.",
        )

    invite.status = schemas.InviteStatus.revoked.value
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
):
    query = db.query(models.Product).filter(models.Product.id == product_id)

    if workspace_id is None:
        query = query.filter(models.Product.workspace_id.is_(None))
    else:
        query = query.filter(models.Product.workspace_id == workspace_id)

    if not include_deleted:
        query = query.filter(models.Product.is_active.is_(True))

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

    new_product = models.Product(
        workspace_id=workspace_id,
        name=name,
        category=product_data.category.strip(),
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
            detail="Invalid product status.",
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
        .filter(models.Product.quantity <= models.Product.minimum_quantity)
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
            detail="Product is already active.",
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
    )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move stock for an inactive product.",
        )

    quantity_before = product.quantity

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


def normalize_category_name(name: str):
    return name.strip()


def get_category_by_id(
    category_id: int,
    db: Session,
    workspace_id: int | None = None,
):
    query = db.query(models.Category).filter(models.Category.id == category_id)

    if workspace_id is None:
        query = query.filter(models.Category.workspace_id.is_(None))
    else:
        query = query.filter(models.Category.workspace_id == workspace_id)

    category = query.first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )

    return category


def get_category_by_name(name: str, db: Session, workspace_id: int):
    normalized_name = normalize_category_name(name)

    return (
        db.query(models.Category)
        .filter(models.Category.workspace_id == workspace_id)
        .filter(models.Category.name == normalized_name)
        .first()
    )


def create_category(
    category_data: schemas.CategoryCreate,
    db: Session,
    workspace_id: int,
    user_id: int | None = None,
):
    name = normalize_category_name(category_data.name)

    existing_category = get_category_by_name(name, db, workspace_id)

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
    page: int = 1,
    limit: int = 20,
):
    query = db.query(models.Category).filter(
        models.Category.workspace_id == workspace_id
    )

    if search:
        query = query.filter(models.Category.name.ilike(f"%{search}%"))

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

        existing_category = get_category_by_name(new_name, db, workspace_id)

        if existing_category and existing_category.id != category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com esse nome neste workspace.",
            )

        update_data["name"] = new_name

    for field, value in update_data.items():
        setattr(category, field, value)

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
    category = get_category_by_id(category_id, db, workspace_id)
    active_products_count = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.category == category.name)
        .filter(models.Product.is_active.is_(True))
        .count()
    )

    if active_products_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category while active products use it.",
        )

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="category.deleted",
        entity_type="category",
        entity_id=category.id,
        metadata={"name": category.name},
    )
    db.delete(category)
    db.commit()

    return None


def get_dashboard_summary(db: Session, workspace_id: int):
    total_products = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .count()
    )

    total_categories = (
        db.query(models.Category)
        .filter(models.Category.workspace_id == workspace_id)
        .count()
    )

    low_stock_products = (
        db.query(models.Product)
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .filter(models.Product.quantity <= models.Product.minimum_quantity)
        .count()
    )

    total_stock_quantity = (
        db.query(func.coalesce(func.sum(models.Product.quantity), 0))
        .filter(models.Product.workspace_id == workspace_id)
        .filter(models.Product.is_active.is_(True))
        .scalar()
    )

    total_stock_movements = (
        db.query(models.StockMovement)
        .filter(models.StockMovement.workspace_id == workspace_id)
        .count()
    )

    return {
        "total_products": total_products,
        "total_categories": total_categories,
        "low_stock_products": low_stock_products,
        "total_stock_quantity": total_stock_quantity,
        "total_stock_movements": total_stock_movements,
    }
