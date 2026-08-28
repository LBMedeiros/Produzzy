from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.config import (
    PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS,
    PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS,
)
from app.dependencies import get_current_user, get_db
from app.services.rate_limit_service import (
    build_rate_limit_key,
    run_with_failure_rate_limit,
)


router = APIRouter(
    tags=["Workspaces"],
)


def accept_invite_with_rate_limit(
    token: str,
    request: Request,
    current_user: models.User,
    db: Session,
):
    scope = "invite.accept"
    key = build_rate_limit_key(request, f"user:{current_user.id}")

    return run_with_failure_rate_limit(
        scope,
        key,
        PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS,
        PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS,
        lambda: crud.accept_workspace_invite(token, current_user, db),
    )


def accept_invite_link_with_rate_limit(
    token: str,
    request: Request,
    current_user: models.User,
    db: Session,
):
    scope = "invite_link.accept"
    key = build_rate_limit_key(request, f"user:{current_user.id}")

    return run_with_failure_rate_limit(
        scope,
        key,
        PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS,
        PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS,
        lambda: crud.accept_workspace_invite_link(token, current_user, db),
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


@router.delete(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workspace(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.delete_workspace(workspace_id, current_user, db)

    return None


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


@router.get(
    "/workspaces/{workspace_id}/team",
    response_model=schemas.WorkspaceTeamResponse,
)
def get_workspace_team(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_workspace_team(workspace_id, current_user, db)


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


@router.post(
    "/workspaces/{workspace_id}/invite-links",
    response_model=schemas.WorkspaceInviteLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace_invite_link(
    workspace_id: int,
    invite_data: schemas.WorkspaceInviteLinkCreate = (
        schemas.WorkspaceInviteLinkCreate()
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_workspace_invite_link(
        workspace_id,
        invite_data,
        current_user,
        db,
    )


@router.post(
    "/workspaces/{workspace_id}/invite-link",
    response_model=schemas.WorkspaceInviteLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace_invite_link_legacy(
    workspace_id: int,
    invite_data: schemas.WorkspaceInviteLinkCreate = (
        schemas.WorkspaceInviteLinkCreate()
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_workspace_invite_link(
        workspace_id,
        invite_data,
        current_user,
        db,
    )


@router.get(
    "/workspaces/{workspace_id}/invite-links",
    response_model=list[schemas.WorkspaceInviteLinkListResponse],
)
def list_workspace_invite_links(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return crud.list_workspace_invite_links(
        workspace_id,
        current_user,
        db,
        page,
        limit,
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
    "/workspaces/{workspace_id}/invite-links/{link_id}/revoke",
    response_model=schemas.WorkspaceInviteLinkResponse,
)
def revoke_workspace_invite_link(
    workspace_id: int,
    link_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.revoke_workspace_invite_link(
        workspace_id,
        link_id,
        current_user,
        db,
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
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return accept_invite_with_rate_limit(token, request, current_user, db)


@router.post(
    "/invite-links/{token}/accept",
    response_model=schemas.WorkspaceMemberResponse,
)
def accept_workspace_invite_link(
    token: str,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return accept_invite_link_with_rate_limit(
        token,
        request,
        current_user,
        db,
    )
