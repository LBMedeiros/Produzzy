from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/workspaces/{workspace_id}/search",
    tags=["Search"],
)


@router.get("", response_model=schemas.WorkspaceSearchResponse)
def search_workspace(
    workspace_id: int,
    q: str = Query(default="", max_length=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.search_workspace(db, workspace_id, q)
