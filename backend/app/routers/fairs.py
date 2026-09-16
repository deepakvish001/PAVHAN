"""Physical fairs, and the stall QR that outlives them."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Exhibition, Order, Product, StallCard, User
from ..services import fairs as fair_service

router = APIRouter(prefix="/api/fairs", tags=["fairs"])


class JoinFair(BaseModel):
    artisan_id: str
    exhibition_id: str | None = None
    stall_number: str = ""


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("")
def list_fairs(db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(Exhibition).where(Exhibition.active.is_(True))).all())
    return {
        "fairs": [
            {
                "id": f.id, "name": f.name, "name_hi": f.name_hi, "venue": f.venue,
                "city": f.city, "organiser": f.organiser,
                "starts_on": f.starts_on, "ends_on": f.ends_on,
                "annual_footfall": f.annual_footfall,
                **fair_service.fair_window(f),
            }
            for f in rows
        ],
        "why": "A fair gives a fortnight of attention. The QR turns that "
               "attention into a customer who can still find you in March.",
        "why_hi": "मेला दो हफ़्ते की भीड़ देता है। यह क्यूआर उस भीड़ को ऐसा ग्राहक बनाता है "
                  "जो मार्च में भी आपको ढूँढ सके।",
    }


@router.post("/stall")
def create_stall(payload: JoinFair, request: Request, db: Session = Depends(get_db)) -> dict:
    """Give this artisan a stall card for a fair (or a standing one)."""
    artisan = db.get(User, payload.artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")
    if payload.exhibition_id and not db.get(Exhibition, payload.exhibition_id):
        raise HTTPException(404, "Exhibition not found")

    existing = db.scalars(
        select(StallCard).where(
            StallCard.artisan_id == payload.artisan_id,
            StallCard.exhibition_id == payload.exhibition_id,
        )).first()
    if existing:
        card = existing
    else:
        code = fair_service.new_code()
        while db.scalars(select(StallCard).where(StallCard.code == code)).first():
            code = fair_service.new_code()
        card = StallCard(
            artisan_id=payload.artisan_id, exhibition_id=payload.exhibition_id,
            code=code, stall_number=payload.stall_number,
        )
        db.add(card)
        db.commit()
        db.refresh(card)

    url = fair_service.stall_url(_base_url(request), card.code)
    return {
        "code": card.code, "url": url, "stall_number": card.stall_number,
        "scans": card.scans, "follows": card.follows,
        "orders_after_fair": card.orders_after_fair,
        "revenue_after_fair": card.revenue_after_fair,
        "qr_svg_url": f"/api/fairs/stall/{card.code}/qr.svg",
    }


@router.get("/stall/{code}/qr.svg")
def stall_qr(code: str, request: Request, db: Session = Depends(get_db)) -> Response:
    card = db.scalars(select(StallCard).where(StallCard.code == code)).first()
    if not card:
        raise HTTPException(404, "Stall not found")
    svg = fair_service.qr_svg(fair_service.stall_url(_base_url(request), code))
    if not svg:
        raise HTTPException(503, "QR generation is unavailable on this deployment")
    return Response(svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.get("/stall/{code}")
def stall_storefront(code: str, follow: bool = False, db: Session = Depends(get_db)) -> dict:
    """What a visitor sees after scanning the card at the stall."""
    card = db.scalars(select(StallCard).where(StallCard.code == code)).first()
    if not card:
        raise HTTPException(404, "That stall code does not exist")

    card.scans += 1
    if follow:
        card.follows += 1
    db.commit()

    artisan = db.get(User, card.artisan_id)
    exhibition = db.get(Exhibition, card.exhibition_id) if card.exhibition_id else None
    products = list(db.scalars(
        select(Product).where(Product.artisan_id == card.artisan_id,
                              Product.published.is_(True))).all())

    return {
        "code": code,
        "artisan": {
            "id": artisan.id, "name": artisan.name, "avatar": artisan.avatar,
            "region": artisan.region, "craft_focus": artisan.craft_focus,
            "experience_years": artisan.experience_years,
        } if artisan else None,
        "exhibition": {
            "name": exhibition.name, "name_hi": exhibition.name_hi,
            "city": exhibition.city, "venue": exhibition.venue,
        } if exhibition else None,
        "stall_number": card.stall_number,
        "products": [
            {"id": p.id, "title": p.title, "title_hi": p.title_hi,
             "price": p.price, "image": (p.images or [None])[0],
             "craft_type": p.craft_type, "region": p.region}
            for p in products
        ],
        "scans": card.scans,
        "follows": card.follows,
    }


@router.get("/stall/{code}/performance")
def stall_performance(code: str, db: Session = Depends(get_db)) -> dict:
    """Did the fair actually carry into the rest of the year?"""
    card = db.scalars(select(StallCard).where(StallCard.code == code)).first()
    if not card:
        raise HTTPException(404, "Stall not found")

    products = list(db.scalars(
        select(Product).where(Product.artisan_id == card.artisan_id)).all())
    ids = [p.id for p in products]
    orders = list(db.scalars(select(Order).where(Order.product_id.in_(ids)))) if ids else []

    exhibition = db.get(Exhibition, card.exhibition_id) if card.exhibition_id else None
    ends = exhibition.ends_on if exhibition else None
    if ends and ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)

    after = []
    for o in orders:
        placed = o.created_at
        if placed and placed.tzinfo is None:
            placed = placed.replace(tzinfo=timezone.utc)
        if ends and placed and placed > ends:
            after.append(o)
        elif o.stall_code == code:
            after.append(o)

    revenue = round(sum(o.artisan_payout for o in after), 2)
    card.orders_after_fair = len(after)
    card.revenue_after_fair = revenue
    db.commit()

    conversion = round(card.follows / card.scans * 100, 1) if card.scans else 0.0
    return {
        "code": code,
        "scans": card.scans,
        "follows": card.follows,
        "follow_rate_percent": conversion,
        "orders_after_fair": len(after),
        "revenue_after_fair": revenue,
        "exhibition": exhibition.name if exhibition else None,
        "ended_on": ends,
        "reading": (
            f"{card.scans} visitors scanned your card and {len(after)} orders came "
            f"in after the fair closed — worth Rs.{revenue:,.0f}. That is income the "
            f"fair would not have produced on its own."
            if after else
            f"{card.scans} visitors scanned your card. No orders have come in since "
            f"the fair yet — keep the listing fresh and they will find you."
        ),
        "reading_hi": (
            f"{card.scans} लोगों ने आपका कार्ड स्कैन किया और मेला ख़त्म होने के बाद "
            f"{len(after)} ऑर्डर आए — ₹{revenue:,.0f} के। यह कमाई मेले से अपने आप नहीं होती।"
            if after else
            f"{card.scans} लोगों ने कार्ड स्कैन किया। अभी कोई ऑर्डर नहीं आया — सामान ताज़ा "
            f"रखिए, वे आपको ढूँढ लेंगे।"
        ),
    }


@router.get("/artisan/{artisan_id}/stalls")
def artisan_stalls(artisan_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    cards = list(db.scalars(
        select(StallCard).where(StallCard.artisan_id == artisan_id)).all())
    base = _base_url(request)
    return {
        "stalls": [
            {
                "code": c.code, "url": fair_service.stall_url(base, c.code),
                "qr_svg_url": f"/api/fairs/stall/{c.code}/qr.svg",
                "stall_number": c.stall_number, "scans": c.scans,
                "follows": c.follows, "orders_after_fair": c.orders_after_fair,
                "revenue_after_fair": c.revenue_after_fair,
                "exhibition": (db.get(Exhibition, c.exhibition_id).name
                               if c.exhibition_id else None),
            }
            for c in cards
        ]
    }
