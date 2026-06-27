from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/workspaces/{workspace_id}/stock-movements",
    tags=["Stock Movements"],
)


@router.get("", response_model=list[schemas.StockMovementResponse])
def list_workspace_stock_movements(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.list_workspace_stock_movements(
        db=db,
        workspace_id=workspace_id,
        page=page,
        limit=limit,
    )
