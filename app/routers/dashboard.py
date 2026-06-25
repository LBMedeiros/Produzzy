from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_dashboard_summary(db)