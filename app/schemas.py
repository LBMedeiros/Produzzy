from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class StockMovementType(str, Enum):
    entrada = "entrada"
    saida = "saida"
    ajuste = "ajuste"


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
    name: str
    category: str
    quantity: int
    minimum_quantity: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockMovementCreate(BaseModel):
    movement_type: StockMovementType
    quantity: int = Field(gt=0)
    reason: Optional[str] = Field(default=None, max_length=255)


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity: int
    quantity_before: int
    quantity_after: int
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    total_products: int
    total_categories: int
    low_stock_products: int
    total_stock_quantity: int
    total_stock_movements: int