from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/workspaces/{workspace_id}/categories",
    tags=["Categories"],
)


@router.post(
    "",
    response_model=schemas.CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    workspace_id: int,
    category_data: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.CATEGORY_WRITE_ROLES,
    )

    return crud.create_category(category_data, db, workspace_id)


@router.get("", response_model=list[schemas.CategoryResponse])
def list_categories(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.list_categories(
        db=db,
        workspace_id=workspace_id,
        search=search,
        page=page,
        limit=limit,
    )


@router.get("/{category_id}", response_model=schemas.CategoryResponse)
def get_category(
    workspace_id: int,
    category_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.READ_ROLES,
    )

    return crud.get_category_by_id(category_id, db, workspace_id)


@router.patch("/{category_id}", response_model=schemas.CategoryResponse)
def update_category(
    workspace_id: int,
    category_id: int,
    category_data: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.CATEGORY_WRITE_ROLES,
    )

    return crud.update_category(category_id, category_data, db, workspace_id)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    workspace_id: int,
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.require_workspace_role(
        workspace_id,
        current_user,
        db,
        crud.CATEGORY_WRITE_ROLES,
    )
    crud.delete_category(category_id, db, workspace_id)

    return None
