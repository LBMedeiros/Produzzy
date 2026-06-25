from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/workspaces/{workspace_id}/audit-logs",
    tags=["Audit Logs"],
)


@router.get("", response_model=list[schemas.AuditLogResponse])
def list_audit_logs(
    workspace_id: int,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.AUDIT_LOG_READ_ROLES,
    )

    return crud.list_audit_logs(
        db=db,
        workspace_id=workspace_id,
        action=action,
        entity_type=entity_type,
        user_id=user_id,
        page=page,
        limit=limit,
    )
