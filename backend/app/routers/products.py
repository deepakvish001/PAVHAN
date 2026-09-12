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


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    if payload.artisan_id and not db.get(User, payload.artisan_id):
        raise HTTPException(400, "Unknown artisan_id")
    product = Product(**payload.model_dump())
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
