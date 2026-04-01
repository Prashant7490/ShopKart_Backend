from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProductOut(BaseModel):
    id: str
    name: str
    description: str
    price: float
    original_price: float
    discount_percent: int
    category: str
    brand: str
    rating: float
    review_count: int
    sold_count: int
    stock: int
    image_url: str
    images: List[str]
    tags: List[str]
    is_featured: bool
    free_delivery: bool
    assured: bool

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: str
    name: str
    icon: str
    image_url: str

    model_config = {"from_attributes": True}


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = 1


class OrderIn(BaseModel):
    session_id: str
    address: dict
    payment_method: str


class OrderOut(BaseModel):
    id: str
    session_id: str
    items: list
    address: dict
    payment_method: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
