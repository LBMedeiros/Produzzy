from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/workspaces/{workspace_id}/replenishments",
    tags=["Replenishments"],
)


@router.get("", response_model=list[schemas.ReplenishmentRequestResponse])
def list_replenishments(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_status: schemas.ReplenishmentStatusFilter | None = Query(
        default=None,
        alias="status",
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.list_replenishment_requests(
        workspace_id=workspace_id,
        db=db,
        request_status=request_status,
        page=page,
        limit=limit,
    )


@router.post(
    "",
    response_model=schemas.ReplenishmentRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_replenishment(
    workspace_id: int,
    request_data: schemas.ReplenishmentRequestCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.REPLENISHMENT_CREATE_ROLES,
    )

    return crud.create_replenishment_request(
        workspace_id=workspace_id,
        request_data=request_data,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/{request_id}/assignees/me",
    response_model=schemas.ReplenishmentRequestResponse,
)
def assign_replenishment_to_me(
    workspace_id: int,
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.REPLENISHMENT_ASSIGN_ROLES,
    )

    return crud.assign_replenishment_user(
        workspace_id=workspace_id,
        request_id=request_id,
        user_id=current_user.id,
        assigned_by_user_id=current_user.id,
        db=db,
    )


@router.delete(
    "/{request_id}/assignees/me",
    response_model=schemas.ReplenishmentRequestResponse,
)
def unassign_replenishment_from_me(
    workspace_id: int,
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.REPLENISHMENT_ASSIGN_ROLES,
    )

    return crud.remove_replenishment_user(
        workspace_id=workspace_id,
        request_id=request_id,
        user_id=current_user.id,
        removed_by_user_id=current_user.id,
        db=db,
    )


@router.post(
    "/{request_id}/assignees/{user_id}",
    response_model=schemas.ReplenishmentRequestResponse,
)
def assign_replenishment_member(
    workspace_id: int,
    request_id: int,
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.REPLENISHMENT_MANAGE_ASSIGNEES_ROLES,
    )

    return crud.assign_replenishment_user(
        workspace_id=workspace_id,
        request_id=request_id,
        user_id=user_id,
        assigned_by_user_id=current_user.id,
        db=db,
    )


@router.delete(
    "/{request_id}/assignees/{user_id}",
    response_model=schemas.ReplenishmentRequestResponse,
)
def remove_replenishment_member(
    workspace_id: int,
    request_id: int,
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.REPLENISHMENT_MANAGE_ASSIGNEES_ROLES,
    )

    return crud.remove_replenishment_user(
        workspace_id=workspace_id,
        request_id=request_id,
        user_id=user_id,
        removed_by_user_id=current_user.id,
        db=db,
    )


@router.get(
    "/{request_id}",
    response_model=schemas.ReplenishmentRequestResponse,
)
def get_replenishment(
    workspace_id: int,
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.get_replenishment_request_by_id(
        workspace_id,
        request_id,
        db,
    )


@router.patch(
    "/{request_id}",
    response_model=schemas.ReplenishmentRequestResponse,
)
def update_replenishment(
    workspace_id: int,
    request_id: int,
    request_data: schemas.ReplenishmentRequestUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.update_replenishment_request(
        workspace_id=workspace_id,
        request_id=request_id,
        request_data=request_data,
        current_user=current_user,
        db=db,
    )
