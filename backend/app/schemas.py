from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class StockMovementType(str, Enum):
    entrada = "entrada"
    saida = "saida"
    ajuste = "ajuste"


class WorkspaceRole(str, Enum):
    owner = "owner"
    admin = "admin"
    employee = "employee"
    viewer = "viewer"


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"


class ProductStatus(str, Enum):
    active = "active"
    deleted = "deleted"
    all = "all"


class CategoryStatus(str, Enum):
    active = "active"
    deleted = "deleted"
    all = "all"


class ReplenishmentType(str, Enum):
    purchase = "purchase"
    production = "production"


class ReplenishmentStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    canceled = "canceled"


class ReplenishmentStatusFilter(str, Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    canceled = "canceled"
    all = "all"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceInviteCreate(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    role: WorkspaceRole


class WorkspaceInviteResponse(BaseModel):
    id: int
    workspace_id: int
    email: str
    role: str
    token: str
    status: str
    invite_url: str
    expires_at: datetime
    created_by_user_id: int
    accepted_by_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0)
    minimum_quantity: int = Field(ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    quantity: Optional[int] = Field(default=None, ge=0)
    minimum_quantity: Optional[int] = Field(default=None, ge=0)


class ProductResponse(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    name: str
    category: str
    quantity: int
    minimum_quantity: int
    is_active: bool
    deleted_at: Optional[datetime] = None
    deleted_by_user_id: Optional[int] = None
    deleted_by_category_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockMovementCreate(BaseModel):
    movement_type: StockMovementType
    quantity: int = Field(gt=0)
    reason: Optional[str] = Field(default=None, max_length=255)


class StockMovementResponse(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    product_id: int
    product_name: Optional[str] = None
    movement_type: str
    quantity: int
    quantity_before: int
    quantity_after: int
    reason: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReplenishmentRequestCreate(BaseModel):
    product_id: int
    type: ReplenishmentType
    quantity_needed: int = Field(gt=0)
    notes: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


class ReplenishmentRequestUpdate(BaseModel):
    type: Optional[ReplenishmentType] = None
    status: Optional[ReplenishmentStatus] = None
    quantity_needed: Optional[int] = Field(default=None, gt=0)
    notes: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


class ReplenishmentAssigneeResponse(BaseModel):
    id: int = Field(validation_alias="user_id")
    name: str
    email: str
    role: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ReplenishmentRequestResponse(BaseModel):
    id: int
    workspace_id: int
    product_id: int
    created_by_user_id: int
    assigned_to_user_id: Optional[int] = None
    type: str
    status: str
    quantity_needed: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    current_quantity: Optional[int] = None
    minimum_quantity: Optional[int] = None
    created_by_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assignees: list[ReplenishmentAssigneeResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryResponse(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    is_active: bool
    deleted_at: Optional[datetime] = None
    deleted_by_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryRestoreResponse(BaseModel):
    category: CategoryResponse
    restored_products_count: int
    skipped_products_count: int


class DashboardSummary(BaseModel):
    total_products: int
    total_categories: int
    low_stock_products: int
    total_stock_quantity: int
    total_stock_movements: int


class AuditLogResponse(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        validation_alias="metadata_json",
    )
    created_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
