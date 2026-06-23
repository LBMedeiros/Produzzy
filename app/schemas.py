from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class StockMovementType(str, Enum):
    entrada = "entrada"
    saida = "saida"
    ajuste = "ajuste"


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