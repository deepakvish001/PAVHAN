"""B2B buyer discovery, matching and enquiries."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Buyer, Enquiry, Product
from ..schemas import BuyerOut, EnquiryCreate
from ..services.matching import buyer_categories, match_buyers

router = APIRouter(prefix="/api/buyers", tags=["buyers"])


@router.get("", response_model=list[BuyerOut])
def list_buyers(db: Session = Depends(get_db), org_type: str | None = None,
                country: str | None = None) -> list[Buyer]:
    stmt = select(Buyer).where(Buyer.active.is_(True))
    if org_type:
        stmt = stmt.where(Buyer.org_type == org_type)
    if country:
        stmt = stmt.where(Buyer.country == country)
    return list(db.scalars(stmt).all())


@router.get("/match/{product_id}")
def match_for_product(
    product_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(8, le=25),
    min_score: int = 0,
) -> dict:
    """The screen that used to say 'select a product' and then show nothing."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if product.artisan and product.artisan.name:
        product._artisan_name = product.artisan.name  # noqa: SLF001 - used by pitch text

    buyers = list(db.scalars(select(Buyer).where(Buyer.active.is_(True))).all())
    matches = match_buyers(product, buyers, limit=limit, min_score=min_score)
    total_opportunity = sum(m.estimated_order_value for m in matches)

    return {
        "product": {
            "id": product.id, "title": product.title,
            "title_hi": product.title_hi, "price": product.price,
            "category": product.category, "craft_type": product.craft_type,
            "image": (product.images or [None])[0],
        },
        "matches": [m.to_dict() for m in matches],
        "categories": buyer_categories(matches),
        "summary": {
            "buyers_scored": len(buyers),
            "matches_returned": len(matches),
            "best_score": matches[0].score if matches else 0,
            "total_opportunity": round(total_opportunity, 0),
            "strong_matches": sum(1 for m in matches if m.score >= 68),
        },
    }


@router.get("/{buyer_id}", response_model=BuyerOut)
def get_buyer(buyer_id: str, db: Session = Depends(get_db)) -> Buyer:
    buyer = db.get(Buyer, buyer_id)
    if not buyer:
        raise HTTPException(404, "Buyer not found")
    return buyer


@router.get("/{buyer_id}/recommended-products")
def recommended_products(buyer_id: str, db: Session = Depends(get_db), limit: int = 12) -> dict:
    """The mirror of matching — what should this buyer be shown first?"""
    buyer = db.get(Buyer, buyer_id)
    if not buyer:
        raise HTTPException(404, "Buyer not found")
    products = list(db.scalars(select(Product).where(Product.published.is_(True))).all())
    scored = []
    for p in products:
        matches = match_buyers(p, [buyer], limit=1)
        if matches:
            scored.append({
                "product_id": p.id, "title": p.title, "title_hi": p.title_hi,
                "price": p.price,
                "image": (p.images or [None])[0], "region": p.region,
                "craft_type": p.craft_type, "moq": p.moq,
                "score": matches[0].score, "fit_label": matches[0].fit_label,
                "unit_price": matches[0].suggested_unit_price,
                "suggested_quantity": matches[0].suggested_quantity,
            })
    scored.sort(key=lambda s: -s["score"])
    return {"buyer": buyer.name, "results": scored[:limit]}


@router.post("/enquiries", status_code=201)
def create_enquiry(payload: EnquiryCreate, db: Session = Depends(get_db)) -> dict:
    product = db.get(Product, payload.product_id)
    buyer = db.get(Buyer, payload.buyer_id)
    if not product or not buyer:
        raise HTTPException(404, "Product or buyer not found")
    qty = max(1, payload.quantity)
    unit = product.price * (0.78 if qty >= 50 else 0.85 if qty >= 20 else 0.92)
    enquiry = Enquiry(
        product_id=product.id, buyer_id=buyer.id, quantity=qty,
        message=payload.message, estimated_value=round(unit * qty, 0),
    )
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)
    return {
        "id": enquiry.id, "status": enquiry.status, "quantity": qty,
        "estimated_value": enquiry.estimated_value, "buyer": buyer.name,
        "product": product.title,
        "message": "Enquiry sent. The buyer typically replies within 2 working days.",
        "message_hi": "पूछताछ भेज दी गई। खरीदार आमतौर पर दो दिन में जवाब देते हैं।",
    }


@router.get("/enquiries/for-artisan/{artisan_id}")
def enquiries_for_artisan(artisan_id: str, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(Enquiry, Product, Buyer)
        .join(Product, Enquiry.product_id == Product.id)
        .join(Buyer, Enquiry.buyer_id == Buyer.id)
        .where(Product.artisan_id == artisan_id)
    ).all()
    return {
        "enquiries": [
            {
                "id": e.id, "status": e.status, "quantity": e.quantity,
                "estimated_value": e.estimated_value, "created_at": e.created_at,
                "product": {"id": p.id, "title": p.title, "title_hi": p.title_hi},
                "buyer": {"id": b.id, "name": b.name, "city": b.city, "logo": b.logo},
            }
            for e, p, b in rows
        ]
    }
