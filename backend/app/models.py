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

    # --- MoSJE scheme linkage -------------------------------------------
    # The ministry funds these units and then loses sight of what happened to
    # the beneficiary's income. Linking the scheme here is what lets real
    # sales become the evidence of whether the assistance worked.
    social_category: Mapped[str] = mapped_column(String(8), default="")
    corporation: Mapped[str] = mapped_column(String(12), default="")
    scheme_name: Mapped[str] = mapped_column(String(120), default="")
    beneficiary_id: Mapped[str] = mapped_column(String(40), default="")
    loan_amount: Mapped[float] = mapped_column(Float, default=0)
    loan_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Monthly income before joining, as stated by the artisan. The honest
    # baseline: self-declared, and labelled as such everywhere it is used.
    baseline_monthly_income: Mapped[float] = mapped_column(Float, default=0)
    shg_name: Mapped[str] = mapped_column(String(120), default="")
    cluster: Mapped[str] = mapped_column(String(120), default="")

    # Where the money actually lands. A VPA rather than an account number
    # because that is what a rural artisan can read off their own phone and
    # check without going to a branch.
    upi_vpa: Mapped[str] = mapped_column(String(80), default="")
    payout_name: Mapped[str] = mapped_column(String(120), default="")
    pincode: Mapped[str] = mapped_column(String(8), default="")
    # Pieces of their own craft this artisan can finish in a month. Used to
    # split a bulk order across a cluster without promising what nobody can
    # make.
    monthly_capacity: Mapped[int] = mapped_column(Integer, default=0)

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
    # Hindi copy, generated alongside the English rather than translated later.
    title_hi: Mapped[str] = mapped_column(String(200), default="")
    short_description_hi: Mapped[str] = mapped_column(String(400), default="")
    detailed_description_hi: Mapped[str] = mapped_column(Text, default="")
    story_hi: Mapped[str] = mapped_column(Text, default="")
    care_hi: Mapped[str] = mapped_column(String(200), default="")

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

    # Set by the offline outbox. A listing catalogued with no signal is held on
    # the phone and sent when the signal returns; if that send is interrupted
    # and retried, this is what stops the artisan ending up with two of the
    # same piece. Blank for anything created online.
    client_ref: Mapped[str] = mapped_column(String(40), default="", index=True)

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


class Exhibition(Base):
    """A physical fair — the thing PAVHAN is meant to make artisans less
    dependent on, by carrying its footfall into the rest of the year."""

    __tablename__ = "exhibitions"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    name: Mapped[str] = mapped_column(String(160))
    name_hi: Mapped[str] = mapped_column(String(160), default="")
    venue: Mapped[str] = mapped_column(String(160), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    organiser: Mapped[str] = mapped_column(String(160), default="")
    starts_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    annual_footfall: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StallCard(Base):
    """An artisan's stall at a fair, and the QR that outlives it.

    A visitor who liked a piece at Surajkund has no way to find that weaver in
    March. A scan here creates that link permanently.
    """

    __tablename__ = "stall_cards"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    exhibition_id: Mapped[str | None] = mapped_column(
        ForeignKey("exhibitions.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    stall_number: Mapped[str] = mapped_column(String(24), default="")
    scans: Mapped[int] = mapped_column(Integer, default=0)
    follows: Mapped[int] = mapped_column(Integer, default=0)
    orders_after_fair: Mapped[int] = mapped_column(Integer, default=0)
    revenue_after_fair: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class BuyerRequirement(Base):
    """What a bulk buyer is looking for, posted so artisans can answer it."""

    __tablename__ = "buyer_requirements"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="", index=True)
    craft_type: Mapped[str] = mapped_column(String(80), default="")
    material: Mapped[str] = mapped_column(String(80), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    budget_min: Mapped[float] = mapped_column(Float, default=0)
    budget_max: Mapped[float] = mapped_column(Float, default=0)
    delivery_days: Mapped[int] = mapped_column(Integer, default=30)
    preferred_regions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="open")
    closes_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Quote(Base):
    """An artisan's answer to a requirement: price, quantity, lead time."""

    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("buyer_requirements.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id"), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=15)
    message: Mapped[str] = mapped_column(Text, default="")
    # sent | accepted | declined | countered
    status: Mapped[str] = mapped_column(String(20), default="sent")
    counter_price: Mapped[float] = mapped_column(Float, default=0)
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
    # Where the sale came from, so the fair bridge can prove it carried
    # footfall into the rest of the year.
    channel: Mapped[str] = mapped_column(String(20), default="retail")
    stall_code: Mapped[str] = mapped_column(String(16), default="")
    quote_id: Mapped[str | None] = mapped_column(ForeignKey("quotes.id"), nullable=True)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Payment(Base):
    """Money moving, and the artisan being able to see where it is.

    The welcome line this app opens with promises the artisan money, not a
    marketplace listing. Until an order could actually be paid for, that was a
    slogan. A Payment row is the thing that makes it true, and its states are
    deliberately the ones an artisan asks about out loud: has the buyer paid,
    is it still being held, has it reached me.
    """

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    amount: Mapped[float] = mapped_column(Float, default=0)
    platform_fee: Mapped[float] = mapped_column(Float, default=0)
    artisan_amount: Mapped[float] = mapped_column(Float, default=0)

    # upi | cod | bank
    method: Mapped[str] = mapped_column(String(12), default="upi")
    # awaiting_payment | held | released | refunded | failed
    state: Mapped[str] = mapped_column(String(20), default="awaiting_payment", index=True)

    payer_name: Mapped[str] = mapped_column(String(120), default="")
    payee_vpa: Mapped[str] = mapped_column(String(80), default="")
    # The UTR a UPI app shows the payer. Typed in by whoever confirms the
    # payment, and carried through to the artisan so both sides quote the same
    # reference when something goes wrong.
    reference: Mapped[str] = mapped_column(String(40), default="")

    timeline: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    held_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Shipment(Base):
    """Getting the piece from the village to the buyer.

    An order that reaches "shipped" with nothing behind it is a status label,
    not a despatch. This row is the despatch: which carrier, at what rate, to
    which pincode, under which AWB.
    """

    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)

    carrier: Mapped[str] = mapped_column(String(24), default="")
    service: Mapped[str] = mapped_column(String(48), default="")
    from_pincode: Mapped[str] = mapped_column(String(8), default="")
    to_pincode: Mapped[str] = mapped_column(String(8), default="")
    weight_g: Mapped[int] = mapped_column(Integer, default=0)
    zone: Mapped[str] = mapped_column(String(24), default="")
    rate: Mapped[float] = mapped_column(Float, default=0)
    promised_days: Mapped[int] = mapped_column(Integer, default=0)

    awb: Mapped[str] = mapped_column(String(24), default="", index=True)
    # booked | picked_up | in_transit | out_for_delivery | delivered
    status: Mapped[str] = mapped_column(String(24), default="booked")
    pickup_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Pool(Base):
    """A cluster answering an order none of its members could fill alone.

    MoSJE works through self-help groups, and the orders worth having are the
    ones a single artisan has to turn down. Six weavers who can each make
    seventy pieces a month cannot individually quote for four hundred; as a
    pool they can, and each one is still paid for exactly what they made.
    """

    __tablename__ = "pools"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("buyer_requirements.id"), index=True)
    lead_artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    shg_name: Mapped[str] = mapped_column(String(120), default="")
    cluster: Mapped[str] = mapped_column(String(120), default="")

    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=30)
    # forming | quoted | awarded | declined
    status: Mapped[str] = mapped_column(String(20), default="forming")
    quote_id: Mapped[str | None] = mapped_column(
        ForeignKey("quotes.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PoolMember(Base):
    """One artisan's share of a pooled order, and what they are owed for it.

    Kept as its own row rather than a blob on the pool, because this is the
    number that decides whether a self-help group trusts the platform a second
    time. It has to be individually visible, individually paid and
    individually disputable.
    """

    __tablename__ = "pool_members"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uid)
    pool_id: Mapped[str] = mapped_column(ForeignKey("pools.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    allocated_qty: Mapped[int] = mapped_column(Integer, default=0)
    capacity_qty: Mapped[int] = mapped_column(Integer, default=0)
    payout: Mapped[float] = mapped_column(Float, default=0)
    # invited | accepted | declined | delivered | paid
    status: Mapped[str] = mapped_column(String(20), default="invited")
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
