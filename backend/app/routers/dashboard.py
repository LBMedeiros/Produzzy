from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/workspaces/{workspace_id}/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.get_dashboard_summary(db, workspace_id)


@router.get("", response_model=schemas.DashboardResponse)
def get_dashboard(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    member = crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.get_dashboard(
        db=db,
        workspace_id=workspace_id,
        include_recent_activity=member.role in crud.AUDIT_LOG_READ_ROLES,
    )
