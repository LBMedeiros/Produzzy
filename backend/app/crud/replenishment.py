"""crud.replenishment — split from the former monolithic crud.py."""
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
from app.crud.products import get_product_by_id

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
        raise NotFound("Necessidade de reposição não encontrada.")

    return replenishment_request

def validate_replenishment_assignee(
    workspace_id: int,
    assigned_to_user_id: int | None,
    db: Session,
):
    if assigned_to_user_id is None:
        return

    if get_workspace_member(workspace_id, assigned_to_user_id, db) is None:
        raise ValidationError("O responsável deve ser membro deste workspace.")

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
        raise Conflict(ACTIVE_REPLENISHMENT_EXISTS)

    # "Quem confirma inicia": the UI always creates a need already assigned to
    # whoever confirmed it, so such a request starts "in progress" instead of
    # waiting as an open need. Created without a responsible (e.g. programmatic
    # callers) it stays "open" as before.
    initial_status = (
        schemas.ReplenishmentStatus.in_progress.value
        if request_data.assigned_to_user_id is not None
        else schemas.ReplenishmentStatus.open.value
    )

    replenishment_request = models.ReplenishmentRequest(
        workspace_id=workspace_id,
        product_id=product.id,
        created_by_user_id=current_user.id,
        assigned_to_user_id=request_data.assigned_to_user_id,
        type=request_data.type.value,
        status=initial_status,
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
            raise Conflict(ACTIVE_REPLENISHMENT_EXISTS) from error

        raise

    return get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )

# Retention windows (see product decision): canceled needs and the chat of
# finalized needs are purged so old records don't pile up forever.
CANCELED_REPLENISHMENT_TTL = timedelta(days=7)
FINALIZED_CHAT_TTL = timedelta(days=30)
REPLENISHMENT_CLEANUP_INTERVAL = timedelta(hours=24)

# Per-process throttle timestamp (no scheduler needed on the free tier): the
# cleanup runs at most once a day, triggered lazily when the board is loaded.
_last_replenishment_cleanup_at = None


def cleanup_old_replenishment_data(db: Session, now=None):
    """Purge data past its retention window: canceled needs after 7 days (with
    their chat and assignees) and the chat of finalized needs after 30 days
    (the need itself is kept as history)."""
    now = now or aware_utc_now()
    canceled_cutoff = now - CANCELED_REPLENISHMENT_TTL
    finalized_chat_cutoff = now - FINALIZED_CHAT_TTL

    canceled_ids = [
        row[0]
        for row in db.query(models.ReplenishmentRequest.id)
        .filter(
            models.ReplenishmentRequest.status
            == schemas.ReplenishmentStatus.canceled.value,
            models.ReplenishmentRequest.updated_at < canceled_cutoff,
        )
        .all()
    ]

    if canceled_ids:
        db.query(models.ReplenishmentMessage).filter(
            models.ReplenishmentMessage.replenishment_id.in_(canceled_ids)
        ).delete(synchronize_session=False)
        db.query(models.ReplenishmentAssignee).filter(
            models.ReplenishmentAssignee.replenishment_id.in_(canceled_ids)
        ).delete(synchronize_session=False)
        db.query(models.ReplenishmentRequest).filter(
            models.ReplenishmentRequest.id.in_(canceled_ids)
        ).delete(synchronize_session=False)

    finalized_ids = [
        row[0]
        for row in db.query(models.ReplenishmentRequest.id)
        .filter(
            models.ReplenishmentRequest.status.in_(
                [
                    schemas.ReplenishmentStatus.completed.value,
                    schemas.ReplenishmentStatus.stocked.value,
                ]
            ),
            models.ReplenishmentRequest.completed_at.isnot(None),
            models.ReplenishmentRequest.completed_at < finalized_chat_cutoff,
        )
        .all()
    ]

    if finalized_ids:
        db.query(models.ReplenishmentMessage).filter(
            models.ReplenishmentMessage.replenishment_id.in_(finalized_ids)
        ).delete(synchronize_session=False)

    db.commit()


def maybe_cleanup_replenishment_data(db: Session):
    """Runs the retention cleanup at most once a day per process, and never lets
    a cleanup failure break the board load that triggered it."""
    global _last_replenishment_cleanup_at
    now = aware_utc_now()

    if (
        _last_replenishment_cleanup_at is not None
        and now - _last_replenishment_cleanup_at < REPLENISHMENT_CLEANUP_INTERVAL
    ):
        return

    # Mark the attempt up front so concurrent board loads don't all run it.
    _last_replenishment_cleanup_at = now

    try:
        cleanup_old_replenishment_data(db, now=now)
    except Exception:
        db.rollback()


def list_replenishment_requests(
    workspace_id: int,
    db: Session,
    request_status: schemas.ReplenishmentStatusFilter | str | None = None,
    page: int = 1,
    limit: int = 20,
):
    maybe_cleanup_replenishment_data(db)

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
        raise ValidationError("Informe ao menos um campo para atualizar.")

    if member.role == schemas.WorkspaceRole.employee.value:
        if set(update_data) != {"status"}:
            raise PermissionDenied("Employee pode atualizar apenas o status.")

        allowed_statuses = {
            schemas.ReplenishmentStatus.in_progress,
            schemas.ReplenishmentStatus.completed,
        }

        if update_data["status"] not in allowed_statuses:
            raise PermissionDenied(
                "Employee pode marcar a necessidade como em andamento "
                "ou concluída."
            )

    for required_field in ("type", "status", "quantity_needed"):
        if required_field in update_data and update_data[required_field] is None:
            raise ValidationError(f"O campo {required_field} não pode ser nulo.")

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
        raise ValidationError(
            "A necessidade precisa estar pronta para estocar antes de ser "
            "marcada como estocada."
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
        raise ValidationError(
            "Não é possível alterar responsáveis de uma necessidade "
            "concluída, estocada ou cancelada."
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
        raise ValidationError("Este usuário já está atribuído à necessidade.")

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
        raise ValidationError("Este usuário já está atribuído à necessidade.")

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
        raise NotFound("Este usuário não está atribuído à necessidade.")

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


def list_replenishment_messages(
    workspace_id: int,
    request_id: int,
    db: Session,
):
    # Raises NotFound if the request is not in this workspace.
    get_replenishment_request_by_id(workspace_id, request_id, db)

    return (
        db.query(models.ReplenishmentMessage)
        .options(joinedload(models.ReplenishmentMessage.user))
        .filter(models.ReplenishmentMessage.replenishment_id == request_id)
        .filter(models.ReplenishmentMessage.workspace_id == workspace_id)
        .order_by(models.ReplenishmentMessage.created_at.asc())
        .all()
    )


def create_replenishment_message(
    workspace_id: int,
    request_id: int,
    body: str,
    current_user: models.User,
    db: Session,
):
    replenishment_request = get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )

    # Only people assigned to the need can comment; everyone can read.
    is_assignee = any(
        assignee.user_id == current_user.id
        for assignee in replenishment_request.assignees
    )

    if not is_assignee:
        raise PermissionDenied(
            "Apenas responsáveis por esta reposição podem comentar."
        )

    message = models.ReplenishmentMessage(
        replenishment_id=request_id,
        workspace_id=workspace_id,
        user_id=current_user.id,
        body=body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return message
