from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    tags=["Workspaces"],
)


@router.get("/workspaces", response_model=list[schemas.WorkspaceResponse])
def list_workspaces(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return crud.list_user_workspaces(current_user, db, page, limit)


@router.post(
    "/workspaces",
    response_model=schemas.WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    workspace_data: schemas.WorkspaceCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_workspace(workspace_data, current_user, db)


@router.get(
    "/workspaces/{workspace_id}",
    response_model=schemas.WorkspaceResponse,
)
def get_workspace(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_workspace_for_user(workspace_id, current_user, db)


@router.patch(
    "/workspaces/{workspace_id}",
    response_model=schemas.WorkspaceResponse,
)
def update_workspace(
    workspace_id: int,
    workspace_data: schemas.WorkspaceUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.update_workspace(workspace_id, workspace_data, current_user, db)


@router.get(
    "/workspaces/{workspace_id}/members",
    response_model=list[schemas.WorkspaceMemberResponse],
)
def list_workspace_members(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return crud.list_workspace_members(
        workspace_id,
        current_user,
        db,
        page,
        limit,
    )


@router.patch(
    "/workspaces/{workspace_id}/members/{member_id}",
    response_model=schemas.WorkspaceMemberResponse,
)
def update_workspace_member(
    workspace_id: int,
    member_id: int,
    member_data: schemas.WorkspaceMemberUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.update_workspace_member(
        workspace_id,
        member_id,
        member_data,
        current_user,
        db,
    )


@router.delete(
    "/workspaces/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workspace_member(
    workspace_id: int,
    member_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.delete_workspace_member(workspace_id, member_id, current_user, db)

    return None


@router.post(
    "/workspaces/{workspace_id}/invites",
    response_model=schemas.WorkspaceInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace_invite(
    workspace_id: int,
    invite_data: schemas.WorkspaceInviteCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_workspace_invite(
        workspace_id,
        invite_data,
        current_user,
        db,
    )


@router.get(
    "/workspaces/{workspace_id}/invites",
    response_model=list[schemas.WorkspaceInviteResponse],
)
def list_workspace_invites(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return crud.list_workspace_invites(
        workspace_id,
        current_user,
        db,
        page,
        limit,
    )


@router.post(
    "/workspaces/{workspace_id}/invites/{invite_id}/revoke",
    response_model=schemas.WorkspaceInviteResponse,
)
def revoke_workspace_invite(
    workspace_id: int,
    invite_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.revoke_workspace_invite(
        workspace_id,
        invite_id,
        current_user,
        db,
    )


@router.post(
    "/invites/{token}/accept",
    response_model=schemas.WorkspaceMemberResponse,
)
def accept_workspace_invite(
    token: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.accept_workspace_invite(token, current_user, db)
