from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/workspaces/{workspace_id}/stock-requests",
    tags=["Stock Requests"],
)


@router.get("", response_model=list[schemas.StockMovementRequestResponse])
def list_stock_requests(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: str = Query(default="pending", alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_READ_ROLES,
    )

    return crud.list_stock_requests(
        workspace_id,
        member,
        db,
        status=status_filter,
        page=page,
        limit=limit,
    )


@router.post(
    "",
    response_model=schemas.StockMovementRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_request(
    workspace_id: int,
    request_data: schemas.StockMovementRequestCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_CREATE_ROLES,
    )

    return crud.create_stock_request(workspace_id, request_data, member, db)


@router.get(
    "/{request_id}",
    response_model=schemas.StockMovementRequestResponse,
)
def get_stock_request(
    workspace_id: int,
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_READ_ROLES,
    )

    return crud.get_stock_request(workspace_id, request_id, member, db)


@router.post(
    "/{request_id}/approve",
    response_model=schemas.StockMovementRequestResponse,
)
def approve_stock_request(
    workspace_id: int,
    request_id: int,
    approve_data: schemas.StockMovementRequestApprove = (
        schemas.StockMovementRequestApprove()
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_REVIEW_ROLES,
    )

    return crud.approve_stock_request(
        workspace_id,
        request_id,
        approve_data,
        member,
        db,
    )


@router.post(
    "/{request_id}/reject",
    response_model=schemas.StockMovementRequestResponse,
)
def reject_stock_request(
    workspace_id: int,
    request_id: int,
    reject_data: schemas.StockMovementRequestReject,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_REVIEW_ROLES,
    )

    return crud.reject_stock_request(
        workspace_id,
        request_id,
        reject_data,
        member,
        db,
    )


@router.post(
    "/{request_id}/cancel",
    response_model=schemas.StockMovementRequestResponse,
)
def cancel_stock_request(
    workspace_id: int,
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_READ_ROLES,
    )

    return crud.cancel_stock_request(workspace_id, request_id, member, db)


@router.get(
    "/{request_id}/messages",
    response_model=list[schemas.StockMovementRequestMessageResponse],
)
def list_stock_request_messages(
    workspace_id: int,
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_READ_ROLES,
    )

    return crud.list_stock_request_messages(workspace_id, request_id, member, db)


@router.post(
    "/{request_id}/messages",
    response_model=schemas.StockMovementRequestMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_stock_request_message(
    workspace_id: int,
    request_id: int,
    message_data: schemas.StockMovementRequestMessageCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.STOCK_REQUEST_READ_ROLES,
    )

    return crud.create_stock_request_message(
        workspace_id,
        request_id,
        message_data.body,
        member,
        db,
    )
