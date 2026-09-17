"""Users, artisan dashboard and retail orders."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Enquiry, Order, Product, User
from ..schemas import OrderCreate, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api", tags=["users"])

PLATFORM_FEE = 0.05  # PAVHAN's flat, visible cut


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), role: str | None = None) -> list[User]:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    return list(db.scalars(stmt).all())


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate,
                db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/artisans/{artisan_id}/dashboard")
def dashboard(artisan_id: str, db: Session = Depends(get_db)) -> dict:
    artisan = db.get(User, artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")

    products = list(db.scalars(select(Product).where(Product.artisan_id == artisan_id)).all())
    product_ids = [p.id for p in products]

    orders = []
    enquiries = []
    if product_ids:
        orders = list(db.scalars(select(Order).where(Order.product_id.in_(product_ids))).all())
        enquiries = list(
            db.scalars(select(Enquiry).where(Enquiry.product_id.in_(product_ids))).all()
        )

    earnings = sum(o.artisan_payout for o in orders)
    gross = sum(o.amount for o in orders)
    pipeline = sum(e.estimated_value for e in enquiries if e.status != "closed")

    # The number that makes the case: what the same work earns through a trader.
    middleman_equivalent = gross * 0.42

    return {
        "artisan": {
            "id": artisan.id, "name": artisan.name, "region": artisan.region,
            "craft_focus": artisan.craft_focus, "avatar": artisan.avatar,
            "experience_years": artisan.experience_years,
        },
        "stats": {
            "products": len(products),
            "published": sum(1 for p in products if p.published),
            "total_views": sum(p.views for p in products),
            "orders": len(orders),
            "earnings": round(earnings, 2),
            "gross_sales": round(gross, 2),
            "pipeline_value": round(pipeline, 2),
            "open_enquiries": sum(1 for e in enquiries if e.status == "sent"),
            "avg_quality": round(
                sum(p.quality_score for p in products) / len(products), 1
            ) if products else 0,
            "extra_vs_middleman": round(earnings - middleman_equivalent, 2),
            "uplift_percent": round(
                (earnings - middleman_equivalent) / max(middleman_equivalent, 1) * 100, 1
            ) if gross else 0,
        },
        "recent_orders": [
            {"id": o.id, "amount": o.amount, "payout": o.artisan_payout,
             "status": o.status, "quantity": o.quantity, "created_at": o.created_at}
            for o in sorted(orders, key=lambda o: o.created_at, reverse=True)[:5]
        ],
        "top_products": [
            {"id": p.id, "title": p.title, "title_hi": p.title_hi,
             "views": p.views, "price": p.price,
             "quality_score": p.quality_score, "image": (p.images or [None])[0]}
            for p in sorted(products, key=lambda p: -p.views)[:5]
        ],
    }


@router.post("/orders", status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> dict:
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    qty = max(1, payload.quantity)
    if product.stock < qty:
        raise HTTPException(409, f"Only {product.stock} left in stock")

    amount = product.price * qty
    payout = round(amount * (1 - PLATFORM_FEE), 2)
    order = Order(
        product_id=product.id, customer_name=payload.customer_name,
        quantity=qty, amount=amount, artisan_payout=payout,
    )
    product.stock -= qty
    db.add(order)
    db.commit()
    db.refresh(order)
    return {
        "id": order.id, "amount": amount, "artisan_payout": payout,
        "platform_fee": round(amount - payout, 2),
        "artisan_share_percent": round((1 - PLATFORM_FEE) * 100, 1),
        "status": order.status, "product": product.title,
        "product_hi": product.title_hi,
    }


@router.get("/stats/platform")
def platform_stats(db: Session = Depends(get_db)) -> dict:
    """Headline numbers for the landing screen."""
    artisans = db.scalar(select(func.count()).select_from(User).where(User.role == "artisan")) or 0
    products = db.scalar(select(func.count()).select_from(Product)) or 0
    buyers = db.scalar(select(func.count()).select_from(Enquiry)) or 0
    paid = db.scalar(select(func.coalesce(func.sum(Order.artisan_payout), 0.0))) or 0.0
    regions = db.scalar(select(func.count(func.distinct(Product.region)))) or 0
    return {
        "artisans": artisans,
        "products": products,
        "enquiries": buyers,
        "paid_to_artisans": round(float(paid), 2),
        "regions_covered": regions,
        "artisan_share_percent": round((1 - PLATFORM_FEE) * 100, 1),
    }
