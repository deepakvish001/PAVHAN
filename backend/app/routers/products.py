"""Product catalogue CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, User
from ..schemas import ProductCreate, ProductOut, ProductUpdate
from ..services import search_engine

router = APIRouter(prefix="/api/products", tags=["products"])


def reindex(db: Session) -> None:
    """Keep the search index in step with the catalogue."""
    products = db.scalars(select(Product).where(Product.published.is_(True))).all()
    search_engine.index.build(list(products))


@router.get("", response_model=list[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    artisan_id: str | None = None,
    category: str | None = None,
    craft_type: str | None = None,
    limit: int = Query(60, le=200),
    offset: int = 0,
    sort: str = "newest",
) -> list[Product]:
    stmt = select(Product).where(Product.published.is_(True))
    if artisan_id:
        stmt = stmt.where(Product.artisan_id == artisan_id)
    if category:
        stmt = stmt.where(Product.category == category)
    if craft_type:
        stmt = stmt.where(Product.craft_type == craft_type)
    products = list(db.scalars(stmt).all())
    key = search_engine.SORTS.get(sort)
    if key:
        products.sort(key=key)
    elif sort == "newest":
        products.sort(key=lambda p: p.created_at or 0, reverse=True)
    return products[offset : offset + limit]


@router.get("/featured", response_model=list[ProductOut])
def featured(db: Session = Depends(get_db), limit: int = 8) -> list[Product]:
    """Highest-signal listings: quality first, then demand."""
    products = list(db.scalars(select(Product).where(Product.published.is_(True))).all())
    products.sort(key=lambda p: (p.quality_score * 1.5 + p.views * 0.2 + p.rating * 8), reverse=True)
    return products[:limit]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    product.views += 1
    db.commit()
    db.refresh(product)
    return product


def _fill_hindi(product: Product) -> None:
    """Give a listing its Hindi half if whoever created it did not.

    The voice flow always sends both halves, so this looks redundant — and it
    is exactly what was missing everywhere else. The seed catalogue, the smoke
    suite, the offline outbox's replay and any future bulk import all reach
    `POST /api/products` directly, and every one of them was quietly
    publishing English-only listings that an artisan browsing in Hindi then
    could not read.

    Putting it here rather than in each caller makes it a property of the
    catalogue instead of a habit of whoever writes the next importer. Existing
    Hindi is never overwritten: a listing the artisan has edited beats a
    generated sentence every time.
    """
    from ..services.listing import hindi_listing
    from ..services.taxonomy import CRAFTS

    if all(getattr(product, f) for f in
           ("title_hi", "short_description_hi", "detailed_description_hi",
            "story_hi", "care_hi")):
        return

    craft = next((c for c in CRAFTS if c.name == product.craft_type), None)
    if craft is None:
        # No recognised craft means no craft vocabulary to write Hindi from,
        # and inventing one would be worse than the English fallback the app
        # already falls back to on screen.
        return

    generated = hindi_listing(
        craft,
        colour=product.colour or "",
        region=product.region or "",
        noun=(product.title or "").split()[-1] if product.title else "",
        size=product.size or "",
        weight=product.weight or "",
        making_days=None,
    )
    for field, value in generated.items():
        if not getattr(product, field, "") and value:
            setattr(product, field, value)


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    if payload.artisan_id and not db.get(User, payload.artisan_id):
        raise HTTPException(400, "Unknown artisan_id")

    # A listing catalogued with no signal waits in the phone's outbox and is
    # sent when the signal returns. That send can be interrupted after the
    # server has committed but before the phone hears the reply — over a 2G
    # connection it regularly is — and the phone will then retry. Returning
    # the listing that already exists, rather than making a second one, is
    # what stops an artisan waking up to two of the same piece.
    if payload.client_ref:
        existing = db.scalars(select(Product).where(
            Product.client_ref == payload.client_ref)).first()
        if existing:
            return existing

    product = Product(**payload.model_dump())
    _fill_hindi(product)
    db.add(product)
    db.commit()
    db.refresh(product)
    reindex(db)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    reindex(db)
    return product


@router.delete("/{product_id}", status_code=204, response_class=Response)
def delete_product(product_id: str, db: Session = Depends(get_db)) -> Response:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    db.delete(product)
    db.commit()
    reindex(db)
    return Response(status_code=204)


@router.get("/{product_id}/similar", response_model=list[ProductOut])
def similar(product_id: str, db: Session = Depends(get_db), limit: int = 6) -> list[Product]:
    """Content-based 'you may also like', scored on shared craft attributes."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    others = db.scalars(
        select(Product).where(Product.id != product_id, Product.published.is_(True))
    ).all()
    tags = set(product.tags or [])

    def score(other: Product) -> float:
        s = 0.0
        if other.craft_type == product.craft_type:
            s += 4
        if other.category == product.category:
            s += 3
        if other.material == product.material:
            s += 2
        if other.region == product.region:
            s += 1.5
        s += len(tags & set(other.tags or [])) * 0.8
        if product.price:
            s += max(0.0, 2 - abs(other.price - product.price) / max(product.price, 1) * 2)
        return s

    return sorted(others, key=score, reverse=True)[:limit]
