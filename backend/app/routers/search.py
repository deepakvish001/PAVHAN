"""Search, autocomplete and facets."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product
from ..schemas import ProductOut, SearchResponse
from ..services import search_engine

router = APIRouter(prefix="/api/search", tags=["search"])


def _all_published(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).where(Product.published.is_(True))).all())


def _ensure_index(db: Session) -> list[Product]:
    products = _all_published(db)
    if len(search_engine.index.docs) != len(products):
        search_engine.index.build(products)
    return products


@router.get("", response_model=SearchResponse)
def search(
    db: Session = Depends(get_db),
    q: str = Query("", description="Free-text query, Hindi or English"),
    category: str | None = None,
    craft_type: str | None = None,
    material: str | None = None,
    region: str | None = None,
    colour: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    gi_only: bool = False,
    max_lead_time: int | None = None,
    min_quality: int | None = None,
    sort: str = "relevance",
    limit: int = Query(30, le=100),
    offset: int = 0,
) -> SearchResponse:
    started = time.perf_counter()
    products = _ensure_index(db)

    filters = {
        "category": category, "craft_type": craft_type, "material": material,
        "region": region, "colour": colour, "min_price": min_price,
        "max_price": max_price, "gi_only": gi_only,
        "max_lead_time": max_lead_time, "min_quality": min_quality,
    }
    filtered = search_engine.apply_filters(products, filters)
    matched_terms: list[str] = []
    did_you_mean = None

    if q.strip():
        hits = search_engine.index.search(q)
        ranking = {h.product_id: h for h in hits}
        results = [p for p in filtered if p.id in ranking]
        results.sort(key=lambda p: ranking[p.id].score, reverse=True)
        for h in hits[:5]:
            matched_terms.extend(h.matched_terms)
        matched_terms = sorted(set(matched_terms))
        if not results:
            did_you_mean = search_engine.index.did_you_mean(q)
    else:
        results = filtered
        if sort == "relevance":
            sort = "popular"

    key = search_engine.SORTS.get(sort)
    if key and (sort != "relevance"):
        results = sorted(results, key=key)

    facets = search_engine.build_facets(filtered)
    page = results[offset : offset + limit]
    return SearchResponse(
        query=q,
        total=len(results),
        took_ms=round((time.perf_counter() - started) * 1000, 2),
        results=[ProductOut.model_validate(p) for p in page],
        facets=facets,
        did_you_mean=did_you_mean,
        matched_terms=matched_terms,
    )


@router.get("/suggest")
def suggest(db: Session = Depends(get_db), q: str = "", limit: int = 8) -> dict:
    _ensure_index(db)
    return {"query": q, "suggestions": search_engine.index.suggest(q, limit)}


@router.get("/facets")
def facets(db: Session = Depends(get_db)) -> dict:
    return search_engine.build_facets(_all_published(db))


@router.get("/trending")
def trending(db: Session = Depends(get_db), limit: int = 8) -> dict:
    """Trending searches, derived from what the catalogue actually contains."""
    products = _all_published(db)
    counts: dict[str, int] = {}
    for p in products:
        for token in (p.craft_type, p.category, p.material, p.region):
            if token:
                counts[token] = counts.get(token, 0) + 1 + int(p.views / 25)
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    return {"trending": [k for k, _ in ordered[:limit]]}
