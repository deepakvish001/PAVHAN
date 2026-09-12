"""Database models for PAVHAN."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """An artisan, a retail customer, a B2B buyer or an exporter."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), default="")
    # artisan | customer | b2b | exporter | ngo
    role: Mapped[str] = mapped_column(String(20), index=True)
    language: Mapped[str] = mapped_column(String(8), default="hi")
    region: Mapped[str] = mapped_column(String(80), default="")
    craft_focus: Mapped[str] = mapped_column(String(120), default="")
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    avatar: Mapped[str] = mapped_column(String(16), default="🧑‍🎨")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    products: Mapped[list[Product]] = relationship(back_populates="artisan")


class Product(Base):
    """A craft listing produced by the AI cataloguer and confirmed by the artisan."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    artisan_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)

    title: Mapped[str] = mapped_column(String(200), index=True)
    short_description: Mapped[str] = mapped_column(String(400), default="")
    detailed_description: Mapped[str] = mapped_column(Text, default="")
    story: Mapped[str] = mapped_column(Text, default="")

    craft_type: Mapped[str] = mapped_column(String(80), index=True, default="")
    category: Mapped[str] = mapped_column(String(80), index=True, default="")
    material: Mapped[str] = mapped_column(String(80), index=True, default="")
    colour: Mapped[str] = mapped_column(String(80), default="")
    region: Mapped[str] = mapped_column(String(80), index=True, default="")
    size: Mapped[str] = mapped_column(String(80), default="")
    weight: Mapped[str] = mapped_column(String(80), default="")
    care: Mapped[str] = mapped_column(String(200), default="")
    technique: Mapped[str] = mapped_column(String(120), default="")

    price: Mapped[float] = mapped_column(Float, default=0)
    price_floor: Mapped[float] = mapped_column(Float, default=0)
    price_premium: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="INR")

    stock: Mapped[int] = mapped_column(Integer, default=1)
    moq: Mapped[int] = mapped_column(Integer, default=1)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)

    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    sustainability_score: Mapped[int] = mapped_column(Integer, default=0)
    gi_tagged: Mapped[bool] = mapped_column(Boolean, default=False)
    handmade: Mapped[bool] = mapped_column(Boolean, default=True)

    tags: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    images: Mapped[list] = mapped_column(JSON, default=list)
    palette: Mapped[list] = mapped_column(JSON, default=list)

    ai_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    pricing_meta: Mapped[dict] = mapped_column(JSON, default=dict)

    views: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    artisan: Mapped[User | None] = relationship(back_populates="products")


class Buyer(Base):
    """A B2B buyer / boutique / exporter profile used by the matching engine."""

    __tablename__ = "buyers"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    name: Mapped[str] = mapped_column(String(160))
    org_type: Mapped[str] = mapped_column(String(60), default="Boutique")
    country: Mapped[str] = mapped_column(String(80), default="India")
    city: Mapped[str] = mapped_column(String(80), default="")
    logo: Mapped[str] = mapped_column(String(16), default="🏬")

    categories: Mapped[list] = mapped_column(JSON, default=list)
    materials: Mapped[list] = mapped_column(JSON, default=list)
    preferred_regions: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)

    budget_min: Mapped[float] = mapped_column(Float, default=0)
    budget_max: Mapped[float] = mapped_column(Float, default=0)
    typical_order_qty: Mapped[int] = mapped_column(Integer, default=50)
    max_lead_time_days: Mapped[int] = mapped_column(Integer, default=30)

    values_sustainability: Mapped[int] = mapped_column(Integer, default=50)
    values_gi_tag: Mapped[int] = mapped_column(Integer, default=50)
    repeat_buyer_score: Mapped[int] = mapped_column(Integer, default=50)
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Enquiry(Base):
    """A B2B enquiry raised from a buyer match."""

    __tablename__ = "enquiries"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="sent")
    estimated_value: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Order(Base):
    """A retail order placed by a customer."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(120), default="Guest")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float] = mapped_column(Float, default=0)
    artisan_payout: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="placed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
