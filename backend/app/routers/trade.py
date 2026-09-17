"""Two-way B2B: buyers post what they need, artisans answer with a price.

Matching already told an artisan which buyers suit a piece they had made.
This is the other direction — a buyer states a requirement, artisans quote
against it, and an accepted quote becomes an order. Without it the "connect
directly with larger B2B buyers" half of the problem statement only works
when the artisan happens to have guessed right.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Buyer, BuyerRequirement, Order, Product, Quote, User

router = APIRouter(prefix="/api/trade", tags=["trade"])

ORDER_STAGES = ["placed", "accepted", "in_production", "shipped", "delivered"]
STAGE_LABELS = {
    "placed": ("Order received", "ऑर्डर मिला"),
    "accepted": ("Accepted by artisan", "कारीगर ने स्वीकार किया"),
    "in_production": ("Being made", "बनाया जा रहा है"),
    "shipped": ("Despatched", "भेज दिया गया"),
    "delivered": ("Delivered", "पहुँच गया"),
    "cancelled": ("Cancelled", "रद्द"),
}


class RequirementIn(BaseModel):
    buyer_id: str
    title: str
    description: str = ""
    category: str = ""
    craft_type: str = ""
    material: str = ""
    quantity: int = 1
    budget_min: float = 0
    budget_max: float = 0
    delivery_days: int = 30
    preferred_regions: list[str] = []


class QuoteIn(BaseModel):
    requirement_id: str
    artisan_id: str
    product_id: str | None = None
    unit_price: float
    quantity: int
    lead_time_days: int = 15
    message: str = ""


def _requirement_out(req: BuyerRequirement, buyer: Buyer | None, quotes: int = 0) -> dict:
    return {
        "id": req.id, "title": req.title, "description": req.description,
        "category": req.category, "craft_type": req.craft_type,
        "material": req.material, "quantity": req.quantity,
        "budget_min": req.budget_min, "budget_max": req.budget_max,
        "delivery_days": req.delivery_days,
        "preferred_regions": req.preferred_regions or [],
        "status": req.status, "created_at": req.created_at,
        "quotes": quotes,
        "total_value": round((req.budget_min + req.budget_max) / 2 * req.quantity, 0),
        "buyer": {"id": buyer.id, "name": buyer.name, "logo": buyer.logo,
                  "org_type": buyer.org_type, "city": buyer.city,
                  "country": buyer.country,
                  "repeat_buyer_score": buyer.repeat_buyer_score} if buyer else None,
    }


# --------------------------------------------------------------- requirements
@router.get("/requirements")
def list_requirements(
    db: Session = Depends(get_db),
    artisan_id: str | None = Query(None, description="Rank for this artisan's work"),
    status: str = "open",
    limit: int = 30,
) -> dict:
    """Open requirements, ranked for the artisan looking at them.

    An artisan should not have to read forty postings to find the two they can
    actually serve, so anything matching their craft, material or region floats
    to the top and the reason is shown.
    """
    stmt = select(BuyerRequirement)
    if status:
        stmt = stmt.where(BuyerRequirement.status == status)
    rows = list(db.scalars(stmt).all())

    products: list[Product] = []
    artisan = db.get(User, artisan_id) if artisan_id else None
    if artisan:
        products = list(db.scalars(
            select(Product).where(Product.artisan_id == artisan.id)).all())

    out = []
    for req in rows:
        buyer = db.get(Buyer, req.buyer_id)
        quote_count = len(list(db.scalars(
            select(Quote).where(Quote.requirement_id == req.id)).all()))
        row = _requirement_out(req, buyer, quote_count)

        score, why, why_hi = 0, [], []
        if products:
            if any(p.craft_type == req.craft_type for p in products) and req.craft_type:
                score += 45
                why.append("you already make this craft")
                why_hi.append("आप यही शिल्प बनाते हैं")
            if any(p.category == req.category for p in products) and req.category:
                score += 25
                why.append("it is your category")
                why_hi.append("यह आपकी श्रेणी है")
            if any(p.material == req.material for p in products) and req.material:
                score += 15
                why.append("you work with this material")
                why_hi.append("आप इसी सामग्री से काम करते हैं")
            in_budget = [p for p in products
                         if req.budget_min <= p.price <= req.budget_max]
            if in_budget:
                score += 15
                why.append("your prices fit their budget")
                why_hi.append("आपके दाम इनके बजट में हैं")
        if artisan and req.preferred_regions and artisan.region in req.preferred_regions:
            score += 10
            why.append("they want your region")
            why_hi.append("इन्हें आपका क्षेत्र चाहिए")

        row["fit_score"] = min(100, score)
        row["fit_reasons"] = why
        row["fit_reasons_hi"] = why_hi
        row["already_quoted"] = bool(artisan and db.scalars(
            select(Quote).where(Quote.requirement_id == req.id,
                                Quote.artisan_id == artisan.id)).first())
        out.append(row)

    out.sort(key=lambda r: (-r["fit_score"], -r["total_value"]))
    return {"requirements": out[:limit], "total": len(out)}


@router.post("/requirements", status_code=201)
def create_requirement(payload: RequirementIn, db: Session = Depends(get_db)) -> dict:
    if not db.get(Buyer, payload.buyer_id):
        raise HTTPException(404, "Buyer not found")
    req = BuyerRequirement(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return _requirement_out(req, db.get(Buyer, req.buyer_id))


@router.get("/requirements/{requirement_id}")
def get_requirement(requirement_id: str, db: Session = Depends(get_db)) -> dict:
    req = db.get(BuyerRequirement, requirement_id)
    if not req:
        raise HTTPException(404, "Requirement not found")
    quotes = list(db.scalars(
        select(Quote).where(Quote.requirement_id == requirement_id)).all())
    return {
        **_requirement_out(req, db.get(Buyer, req.buyer_id), len(quotes)),
        "quote_list": [
            {
                "id": q.id, "artisan_id": q.artisan_id,
                "artisan": (db.get(User, q.artisan_id).name
                            if db.get(User, q.artisan_id) else ""),
                "unit_price": q.unit_price, "quantity": q.quantity,
                "total": round(q.unit_price * q.quantity, 0),
                "lead_time_days": q.lead_time_days, "message": q.message,
                "status": q.status, "created_at": q.created_at,
            }
            for q in sorted(quotes, key=lambda q: q.unit_price)
        ],
    }


# --------------------------------------------------------------------- quotes
@router.post("/quotes", status_code=201)
def create_quote(payload: QuoteIn, db: Session = Depends(get_db)) -> dict:
    req = db.get(BuyerRequirement, payload.requirement_id)
    if not req:
        raise HTTPException(404, "Requirement not found")
    if req.status != "open":
        raise HTTPException(409, "This requirement is no longer open")
    if not db.get(User, payload.artisan_id):
        raise HTTPException(404, "Artisan not found")

    existing = db.scalars(select(Quote).where(
        Quote.requirement_id == payload.requirement_id,
        Quote.artisan_id == payload.artisan_id)).first()
    if existing:
        raise HTTPException(409, "You have already quoted on this requirement")

    quote = Quote(**payload.model_dump())
    db.add(quote)
    db.commit()
    db.refresh(quote)

    total = round(quote.unit_price * quote.quantity, 0)
    return {
        "id": quote.id, "status": quote.status, "total": total,
        "message": f"Quote sent: {quote.quantity} pieces at Rs.{quote.unit_price:,.0f} "
                   f"each, Rs.{total:,.0f} in total.",
        "message_hi": f"भाव भेज दिया: {quote.quantity} पीस, ₹{quote.unit_price:,.0f} "
                      f"प्रति पीस, कुल ₹{total:,.0f}।",
    }


@router.get("/quotes/artisan/{artisan_id}")
def artisan_quotes(artisan_id: str, db: Session = Depends(get_db)) -> dict:
    quotes = list(db.scalars(select(Quote).where(Quote.artisan_id == artisan_id)).all())
    out = []
    for q in quotes:
        req = db.get(BuyerRequirement, q.requirement_id)
        buyer = db.get(Buyer, req.buyer_id) if req else None
        out.append({
            "id": q.id, "status": q.status, "unit_price": q.unit_price,
            "quantity": q.quantity, "total": round(q.unit_price * q.quantity, 0),
            "lead_time_days": q.lead_time_days, "created_at": q.created_at,
            "counter_price": q.counter_price,
            "requirement": {"id": req.id, "title": req.title} if req else None,
            "buyer": {"name": buyer.name, "logo": buyer.logo} if buyer else None,
        })
    return {"quotes": sorted(out, key=lambda q: str(q["created_at"]), reverse=True)}


@router.post("/quotes/{quote_id}/accept")
def accept_quote(quote_id: str, db: Session = Depends(get_db)) -> dict:
    """The buyer accepts. That is what turns a conversation into an order."""
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    if quote.status == "accepted":
        raise HTTPException(409, "This quote was already accepted")

    req = db.get(BuyerRequirement, quote.requirement_id)
    buyer = db.get(Buyer, req.buyer_id) if req else None

    product = db.get(Product, quote.product_id) if quote.product_id else None
    if not product:
        product = db.scalars(select(Product).where(
            Product.artisan_id == quote.artisan_id).limit(1)).first()
    if not product:
        raise HTTPException(400, "This artisan has no product to attach the order to")

    amount = round(quote.unit_price * quote.quantity, 2)
    now = datetime.now(timezone.utc)
    order = Order(
        product_id=product.id,
        customer_name=buyer.name if buyer else "B2B buyer",
        quantity=quote.quantity,
        amount=amount,
        artisan_payout=round(amount * 0.95, 2),
        status="accepted",
        channel="b2b",
        quote_id=quote.id,
        timeline=[
            {"stage": "placed", "at": now.isoformat(),
             "note": f"Quote accepted by {buyer.name if buyer else 'the buyer'}"},
            {"stage": "accepted", "at": now.isoformat(), "note": "Order confirmed"},
        ],
    )
    quote.status = "accepted"
    if req:
        req.status = "awarded"
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id, "amount": amount,
        "artisan_payout": order.artisan_payout,
        "quantity": quote.quantity, "status": order.status,
        "message": f"Order created for {quote.quantity} pieces, Rs.{amount:,.0f}.",
        "message_hi": f"{quote.quantity} पीस का ऑर्डर बन गया, ₹{amount:,.0f}।",
    }


# --------------------------------------------------------------------- orders
@router.get("/orders/artisan/{artisan_id}")
def artisan_orders(artisan_id: str, db: Session = Depends(get_db)) -> dict:
    products = list(db.scalars(
        select(Product).where(Product.artisan_id == artisan_id)).all())
    by_id = {p.id: p for p in products}
    orders = list(db.scalars(
        select(Order).where(Order.product_id.in_(list(by_id))))) if by_id else []

    def stage_index(order: Order) -> int:
        return ORDER_STAGES.index(order.status) if order.status in ORDER_STAGES else 0

    out = []
    for o in sorted(orders, key=lambda o: o.created_at or datetime.min, reverse=True):
        product = by_id.get(o.product_id)
        out.append({
            "id": o.id, "status": o.status,
            "status_label": STAGE_LABELS.get(o.status, (o.status, o.status))[0],
            "status_label_hi": STAGE_LABELS.get(o.status, (o.status, o.status))[1],
            "stage_index": stage_index(o),
            "quantity": o.quantity, "amount": o.amount,
            "artisan_payout": o.artisan_payout, "channel": o.channel,
            "customer_name": o.customer_name, "created_at": o.created_at,
            "timeline": o.timeline or [],
            "product": {"id": product.id, "title": product.title,
                        "title_hi": product.title_hi,
                        "image": (product.images or [None])[0]} if product else None,
        })

    return {
        "orders": out,
        "stages": [{"key": s, "label": STAGE_LABELS[s][0],
                    "label_hi": STAGE_LABELS[s][1]} for s in ORDER_STAGES],
        "summary": {
            "total": len(out),
            "open": sum(1 for o in out if o["status"] not in ("delivered", "cancelled")),
            "earnings": round(sum(o["artisan_payout"] for o in out), 2),
            "pipeline": round(sum(o["artisan_payout"] for o in out
                                  if o["status"] not in ("delivered", "cancelled")), 2),
        },
    }


@router.post("/orders/{order_id}/advance")
def advance_order(order_id: str, to: str = Query(...), db: Session = Depends(get_db)) -> dict:
    """Move an order one stage on, and record when."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if to not in ORDER_STAGES and to != "cancelled":
        raise HTTPException(400, f"Stage must be one of {ORDER_STAGES + ['cancelled']}")
    if to != "cancelled" and order.status in ORDER_STAGES:
        if ORDER_STAGES.index(to) < ORDER_STAGES.index(order.status):
            raise HTTPException(409, "An order cannot move backwards")

    order.status = to
    timeline = list(order.timeline or [])
    timeline.append({
        "stage": to, "at": datetime.now(timezone.utc).isoformat(),
        "note": STAGE_LABELS.get(to, (to, to))[0],
    })
    order.timeline = timeline
    db.commit()
    return {
        "id": order.id, "status": order.status, "timeline": order.timeline,
        "label": STAGE_LABELS.get(to, (to, to))[0],
        "label_hi": STAGE_LABELS.get(to, (to, to))[1],
    }
