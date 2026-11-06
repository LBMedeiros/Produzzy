"""crud.stock_requests — stock movement requests.

A Solicitante asks for an entrada/saída; Operação and up approve it (which
records the real stock movement, with every usual stock rule) or reject it;
the requester can cancel while it is pending. Requesters only see their own
requests; reviewers see all of the workspace's.
"""
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.crud.base import *  # noqa: F401,F403
from app.crud.products import get_product_by_id
from app.crud.stock import create_stock_movement

STOCK_REQUEST_OPEN_STATUSES = {schemas.StockMovementRequestStatus.pending.value}
STOCK_REQUEST_LIST_FILTERS = {
    "all",
    "closed",
    *(status.value for status in schemas.StockMovementRequestStatus),
}


def is_stock_request_reviewer(member: models.WorkspaceMember):
    return member.role in STOCK_REQUEST_REVIEW_ROLES


def stock_request_metadata(stock_request: models.StockMovementRequest):
    return {
        "product_id": stock_request.product_id,
        "movement_type": stock_request.movement_type,
        "requested_quantity": stock_request.requested_quantity,
        "approved_quantity": stock_request.approved_quantity,
        "requested_by_user_id": stock_request.requested_by_user_id,
        "status": stock_request.status,
    }


def get_stock_request(
    workspace_id: int,
    request_id: int,
    member: models.WorkspaceMember,
    db: Session,
    for_update: bool = False,
):
    query = (
        db.query(models.StockMovementRequest)
        .filter(models.StockMovementRequest.workspace_id == workspace_id)
        .filter(models.StockMovementRequest.id == request_id)
    )

    if for_update and db.bind is not None and db.bind.dialect.name != "sqlite":
        query = query.with_for_update()
    else:
        query = query.options(
            joinedload(models.StockMovementRequest.product),
            joinedload(models.StockMovementRequest.requested_by_user),
            joinedload(models.StockMovementRequest.reviewed_by_user),
        )

    stock_request = query.first()

    # A requester only reaches their own requests; anything else reads as
    # missing so other people's requests are not disclosed.
    if stock_request is None or (
        not is_stock_request_reviewer(member)
        and stock_request.requested_by_user_id != member.user_id
    ):
        raise NotFound("Solicitação não encontrada.")

    return stock_request


def list_stock_requests(
    workspace_id: int,
    member: models.WorkspaceMember,
    db: Session,
    status: str = "pending",
    page: int = 1,
    limit: int = 50,
):
    if status not in STOCK_REQUEST_LIST_FILTERS:
        raise ValidationError("Filtro de status inválido.")

    query = (
        db.query(models.StockMovementRequest)
        .options(
            joinedload(models.StockMovementRequest.product),
            joinedload(models.StockMovementRequest.requested_by_user),
            joinedload(models.StockMovementRequest.reviewed_by_user),
        )
        .filter(models.StockMovementRequest.workspace_id == workspace_id)
    )

    if not is_stock_request_reviewer(member):
        query = query.filter(
            models.StockMovementRequest.requested_by_user_id == member.user_id
        )

    if status == "closed":
        query = query.filter(
            models.StockMovementRequest.status.notin_(STOCK_REQUEST_OPEN_STATUSES)
        )
    elif status != "all":
        query = query.filter(models.StockMovementRequest.status == status)

    query = query.order_by(
        models.StockMovementRequest.created_at.desc(),
        models.StockMovementRequest.id.desc(),
    )

    return paginate_query(query, page, limit).all()


def create_stock_request(
    workspace_id: int,
    request_data: schemas.StockMovementRequestCreate,
    member: models.WorkspaceMember,
    db: Session,
):
    if request_data.movement_type not in {
        schemas.StockMovementType.entrada,
        schemas.StockMovementType.saida,
    }:
        raise ValidationError("Só é possível solicitar entrada ou saída.")

    product = get_product_by_id(request_data.product_id, db, workspace_id)

    if (
        request_data.movement_type == schemas.StockMovementType.saida
        and request_data.quantity > product.quantity
    ):
        raise ValidationError("Quantidade de saída maior que o estoque atual.")

    stock_request = models.StockMovementRequest(
        workspace_id=workspace_id,
        product_id=product.id,
        requested_by_user_id=member.user_id,
        movement_type=request_data.movement_type.value,
        status=schemas.StockMovementRequestStatus.pending.value,
        requested_quantity=request_data.quantity,
        reason=request_data.reason,
    )
    db.add(stock_request)
    db.flush()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        action="stock_request.created",
        entity_type="stock_movement_request",
        entity_id=stock_request.id,
        metadata=stock_request_metadata(stock_request),
    )
    db.commit()

    return get_stock_request(workspace_id, stock_request.id, member, db)


def ensure_stock_request_pending(stock_request: models.StockMovementRequest):
    if stock_request.status != schemas.StockMovementRequestStatus.pending.value:
        raise ValidationError("Esta solicitação já foi analisada ou cancelada.")


def approve_stock_request(
    workspace_id: int,
    request_id: int,
    approve_data: schemas.StockMovementRequestApprove,
    member: models.WorkspaceMember,
    db: Session,
):
    # Row lock: two reviewers approving at once cannot both move stock.
    stock_request = get_stock_request(
        workspace_id, request_id, member, db, for_update=True
    )
    ensure_stock_request_pending(stock_request)

    quantity = approve_data.quantity or stock_request.requested_quantity

    if quantity != stock_request.requested_quantity and not approve_data.note:
        raise ValidationError("Informe o motivo da alteração da quantidade.")

    movement_reason = f"Solicitação #{stock_request.id}: {stock_request.reason}"
    movement = create_stock_movement(
        workspace_id=workspace_id,
        product_id=stock_request.product_id,
        movement_data=schemas.StockMovementCreate(
            movement_type=stock_request.movement_type,
            quantity=quantity,
            reason=movement_reason[:255],
        ),
        db=db,
        user_id=member.user_id,
        commit=False,
    )

    stock_request.status = schemas.StockMovementRequestStatus.approved.value
    stock_request.approved_quantity = quantity
    stock_request.review_note = approve_data.note
    stock_request.reviewed_by_user_id = member.user_id
    stock_request.reviewed_at = aware_utc_now()
    stock_request.stock_movement_id = movement.id
    metadata = stock_request_metadata(stock_request)
    metadata["stock_movement_id"] = movement.id
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        action="stock_request.approved",
        entity_type="stock_movement_request",
        entity_id=stock_request.id,
        metadata=metadata,
    )
    db.commit()

    return get_stock_request(workspace_id, request_id, member, db)


def reject_stock_request(
    workspace_id: int,
    request_id: int,
    reject_data: schemas.StockMovementRequestReject,
    member: models.WorkspaceMember,
    db: Session,
):
    stock_request = get_stock_request(
        workspace_id, request_id, member, db, for_update=True
    )
    ensure_stock_request_pending(stock_request)

    stock_request.status = schemas.StockMovementRequestStatus.rejected.value
    stock_request.review_note = reject_data.note
    stock_request.reviewed_by_user_id = member.user_id
    stock_request.reviewed_at = aware_utc_now()
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        action="stock_request.rejected",
        entity_type="stock_movement_request",
        entity_id=stock_request.id,
        metadata=stock_request_metadata(stock_request),
    )
    db.commit()

    return get_stock_request(workspace_id, request_id, member, db)


def cancel_stock_request(
    workspace_id: int,
    request_id: int,
    member: models.WorkspaceMember,
    db: Session,
):
    stock_request = get_stock_request(
        workspace_id, request_id, member, db, for_update=True
    )

    if stock_request.requested_by_user_id != member.user_id:
        raise PermissionDenied("Apenas quem pediu pode cancelar a solicitação.")

    ensure_stock_request_pending(stock_request)

    stock_request.status = schemas.StockMovementRequestStatus.canceled.value
    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        action="stock_request.canceled",
        entity_type="stock_movement_request",
        entity_id=stock_request.id,
        metadata=stock_request_metadata(stock_request),
    )
    db.commit()

    return get_stock_request(workspace_id, request_id, member, db)


def list_stock_request_messages(
    workspace_id: int,
    request_id: int,
    member: models.WorkspaceMember,
    db: Session,
):
    # Raises NotFound when the member cannot see the request.
    get_stock_request(workspace_id, request_id, member, db)

    return (
        db.query(models.StockMovementRequestMessage)
        .options(joinedload(models.StockMovementRequestMessage.user))
        .filter(models.StockMovementRequestMessage.request_id == request_id)
        .filter(models.StockMovementRequestMessage.workspace_id == workspace_id)
        .order_by(
            models.StockMovementRequestMessage.created_at.asc(),
            models.StockMovementRequestMessage.id.asc(),
        )
        .all()
    )


def create_stock_request_message(
    workspace_id: int,
    request_id: int,
    body: str,
    member: models.WorkspaceMember,
    db: Session,
):
    # The requester and every reviewer take part in the conversation.
    get_stock_request(workspace_id, request_id, member, db)

    message = models.StockMovementRequestMessage(
        request_id=request_id,
        workspace_id=workspace_id,
        user_id=member.user_id,
        body=body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return message
