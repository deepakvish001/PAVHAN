"""Share links, which in India means WhatsApp links.

Every endpoint here returns a ready-to-send message plus the `wa.me` URL that
opens it. Nothing is sent from the server: the message opens in the sender's
own WhatsApp and they press send, which needs no Business API, no template
approval and no per-message cost, and works on day one from a phone at a fair.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Product, StallCard, User
from ..services import share

router = APIRouter(prefix="/api/share", tags=["share"])


def _base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _pack(text: str, phone: str = "") -> dict:
    return {"text": text, "whatsapp": share.wa_link(phone, text),
            "phone": share.normalise_phone(phone)}


@router.get("/product/{product_id}")
def product(product_id: str, request: Request, lang: str = Query("en"),
            phone: str = Query(""), db: Session = Depends(get_db)) -> dict:
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    artisan = db.get(User, p.artisan_id) if p.artisan_id else None
    url = f"{_base(request)}/product/{p.id}"
    title = (p.title_hi or p.title) if lang == "hi" else p.title
    text = share.product_share(
        title=title, price=p.price,
        artisan_name=artisan.name if artisan else "a PAVHAN artisan",
        region=p.region or (artisan.region if artisan else "India"),
        url=url, lang=lang)
    return {"url": url, **_pack(text, phone)}


@router.get("/order/{order_id}")
def order(order_id: str, lang: str = Query("hi"),
          db: Session = Depends(get_db)) -> dict:
    """The 'you have an order' message, addressed to the artisan's own phone."""
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    p = db.get(Product, o.product_id)
    artisan = db.get(User, p.artisan_id) if p and p.artisan_id else None
    text = share.order_placed(
        artisan_name=artisan.name if artisan else "artisan",
        buyer_name=o.customer_name, quantity=o.quantity,
        amount=o.amount, payout=o.artisan_payout, order_id=o.id, lang=lang)
    return _pack(text, artisan.phone if artisan else "")


@router.get("/stall/{code}")
def stall(code: str, request: Request, lang: str = Query("en"),
          db: Session = Depends(get_db)) -> dict:
    card = db.scalars(select(StallCard).where(StallCard.code == code)).first()
    if not card:
        raise HTTPException(404, "No stall with that code")
    artisan = db.get(User, card.artisan_id)
    url = f"{_base(request)}/s/{card.code}"
    text = share.stall_share(
        artisan_name=artisan.name if artisan else "a PAVHAN artisan",
        fair_name="the fair", url=url, lang=lang)
    return {"url": url, **_pack(text)}
