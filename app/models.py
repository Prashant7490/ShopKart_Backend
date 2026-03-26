from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"
    id        = Column(String, primary_key=True)
    name      = Column(String(100), nullable=False)
    icon      = Column(String(10), default="🛍️")
    image_url = Column(String, default="")
    products  = relationship("Product", back_populates="category_rel")


class Product(Base):
    __tablename__ = "products"
    id               = Column(String, primary_key=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text, default="")
    price            = Column(Float, nullable=False)
    original_price   = Column(Float, nullable=False)
    discount_percent = Column(Integer, default=0)
    category         = Column(String, ForeignKey("categories.id"))
    brand            = Column(String(100), default="")
    rating           = Column(Float, default=0.0)
    review_count     = Column(Integer, default=0)
    sold_count       = Column(Integer, default=0)
    stock            = Column(Integer, default=0)
    image_url        = Column(String, default="")
    images           = Column(JSON, default=list)
    tags             = Column(JSON, default=list)
    is_featured      = Column(Boolean, default=False)
    free_delivery    = Column(Boolean, default=False)
    assured          = Column(Boolean, default=False)
    category_rel     = relationship("Category", back_populates="products")
    wishlist_items   = relationship("Wishlist", back_populates="product")


class User(Base):
    __tablename__ = "users"
    id              = Column(String, primary_key=True)
    name            = Column(String(150), nullable=False)
    email           = Column(String(200), unique=True, nullable=False, index=True)
    phone           = Column(String(15), default="")
    hashed_password = Column(String, nullable=False)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.now)
    orders          = relationship("Order",    back_populates="user")
    wishlist        = relationship("Wishlist", back_populates="user")
    addresses       = relationship("Address",  back_populates="user")
    reset_tokens    = relationship("PasswordResetToken", back_populates="user")


class Address(Base):
    __tablename__ = "addresses"
    id         = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    name       = Column(String(150), default="")
    phone      = Column(String(15), default="")
    street     = Column(String(300), default="")
    city       = Column(String(100), default="")
    state      = Column(String(100), default="")
    pincode    = Column(String(10), default="")
    is_default = Column(Boolean, default=False)
    user       = relationship("User", back_populates="addresses")


class Wishlist(Base):
    __tablename__ = "wishlist"
    id         = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    added_at   = Column(DateTime, default=datetime.now)
    user       = relationship("User",    back_populates="wishlist")
    product    = relationship("Product", back_populates="wishlist_items")


class Order(Base):
    __tablename__ = "orders"
    id                = Column(String, primary_key=True)
    user_id           = Column(String, ForeignKey("users.id"), nullable=True)
    session_id        = Column(String, nullable=False)
    items             = Column(JSON, default=list)
    address           = Column(JSON, default=dict)
    payment_method    = Column(String(50), default="cod")
    payment_id        = Column(String, default="")
    razorpay_order_id = Column(String, default="")
    payment_status    = Column(String(50), default="pending")
    status            = Column(String(50), default="Confirmed")
    total_amount      = Column(Float, default=0.0)
    created_at        = Column(DateTime, default=datetime.now)
    user              = relationship("User", back_populates="orders")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id         = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    token      = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)
    user       = relationship("User", back_populates="reset_tokens")
