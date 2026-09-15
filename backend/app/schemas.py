"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    role: str
    language: str = "hi"
    region: str = ""
    craft_focus: str = ""
    experience_years: int = 0
    avatar: str = "🧑‍🎨"
    phone: str = ""


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = "artisan"
    language: str = "hi"
    region: str = ""
    craft_focus: str = ""
    phone: str = ""
    experience_years: int = 0


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    artisan_id: str | None = None
    title: str
    short_description: str = ""
    detailed_description: str = ""
    story: str = ""
    title_hi: str = ""
    short_description_hi: str = ""
    detailed_description_hi: str = ""
    story_hi: str = ""
    craft_type: str = ""
    category: str = ""
    material: str = ""
    colour: str = ""
    region: str = ""
    size: str = ""
    weight: str = ""
    care: str = ""
    care_hi: str = ""
    technique: str = ""
    price: float = 0
    price_floor: float = 0
    price_premium: float = 0
    currency: str = "INR"
    stock: int = 1
    moq: int = 1
    lead_time_days: int = 7
    quality_score: int = 0
    sustainability_score: int = 0
    gi_tagged: bool = False
    handmade: bool = True
    tags: list[str] = []
    keywords: list[str] = []
    images: list[str] = []
    palette: list[dict] = []
    ai_meta: dict = {}
    pricing_meta: dict = {}
    views: int = 0
    rating: float = 0
    published: bool = True
    created_at: datetime | None = None


class ProductCreate(BaseModel):
    title: str
    short_description: str = ""
    detailed_description: str = ""
    story: str = ""
    title_hi: str = ""
    short_description_hi: str = ""
    detailed_description_hi: str = ""
    story_hi: str = ""
    care_hi: str = ""
    craft_type: str = ""
    category: str = ""
    material: str = ""
    colour: str = ""
    region: str = ""
    size: str = ""
    weight: str = ""
    care: str = ""
    technique: str = ""
    price: float = 0
    price_floor: float = 0
    price_premium: float = 0
    stock: int = 1
    moq: int = 1
    lead_time_days: int = 7
    quality_score: int = 0
    sustainability_score: int = 0
    gi_tagged: bool = False
    tags: list[str] = []
    keywords: list[str] = []
    images: list[str] = []
    palette: list[dict] = []
    ai_meta: dict = {}
    pricing_meta: dict = {}
    artisan_id: str | None = None


class ProductUpdate(BaseModel):
    title: str | None = None
    short_description: str | None = None
    detailed_description: str | None = None
    price: float | None = None
    stock: int | None = None
    published: bool | None = None
    size: str | None = None
    weight: str | None = None
    care: str | None = None
    colour: str | None = None
    material: str | None = None
    region: str | None = None
    craft_type: str | None = None
    category: str | None = None
    tags: list[str] | None = None


class GenerateListingRequest(BaseModel):
    transcript: str = ""
    image_id: str | None = None
    language: str = "hi"
    artisan_id: str | None = None
    use_llm: bool = True


class PriceRequest(BaseModel):
    craft_key: str | None = None
    craft_type: str | None = None
    complexity: float = 1.0
    making_days: float | None = None
    making_hours: float | None = None
    region: str = ""
    skill_band: str | None = None
    material_cost: float | None = None
    quality_score: int = 70
    gi_tagged: bool | None = None
    natural_dye: bool = False
    channel: str = "direct"
    quantity: int = 1
    artisan_expectation: float | None = None


class BuyerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    org_type: str
    country: str
    city: str
    logo: str
    categories: list[str] = []
    materials: list[str] = []
    preferred_regions: list[str] = []
    certifications: list[str] = []
    budget_min: float = 0
    budget_max: float = 0
    typical_order_qty: int = 0
    max_lead_time_days: int = 30
    values_sustainability: int = 50
    values_gi_tag: int = 50
    repeat_buyer_score: int = 50
    notes: str = ""


class EnquiryCreate(BaseModel):
    product_id: str
    buyer_id: str
    quantity: int = 1
    message: str = ""


class OrderCreate(BaseModel):
    product_id: str
    customer_name: str = "Guest"
    quantity: int = 1


class SearchResponse(BaseModel):
    query: str
    total: int
    took_ms: float
    results: list[ProductOut]
    facets: dict[str, Any] = {}
    did_you_mean: str | None = None
    matched_terms: list[str] = []
