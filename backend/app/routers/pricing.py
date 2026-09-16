"""Price recommendation endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product
from ..schemas import PriceRequest
from ..services import pricing_ml
from ..services.pricing import CHANNEL_MARGIN, SEASON_INDEX, SEASON_LABEL, recommend_price
from ..services.taxonomy import CRAFT_INDEX, CRAFTS

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


def _resolve_craft(craft_key: str | None, craft_type: str | None):
    if craft_key and craft_key in CRAFT_INDEX:
        return CRAFT_INDEX[craft_key]
    if craft_type:
        for craft in CRAFTS:
            if craft.name.lower() == craft_type.lower():
                return craft
        for craft in CRAFTS:
            if craft_type.lower() in craft.name.lower():
                return craft
    return None


@router.get("/model")
def model_card() -> dict:
    """What the machine-learning model is and how accurate it measured itself to be."""
    return pricing_ml.model_card()


@router.post("/recommend")
def recommend(payload: PriceRequest) -> dict:
    """Price a piece with both engines.

    The cost-plus engine answers "what is this worth and here is the
    arithmetic"; the trained model answers "what does this market pay for
    pieces like this". Both are returned, along with a reconciliation that
    says what to do when they disagree.
    """
    craft = _resolve_craft(payload.craft_key, payload.craft_type)
    if not craft:
        raise HTTPException(
            400, "Unknown craft. Pass craft_key (see /api/pricing/crafts) or a craft_type name."
        )
    rec = recommend_price(
        craft,
        complexity=payload.complexity,
        making_days=payload.making_days,
        making_hours=payload.making_hours,
        region=payload.region or (craft.regions[0] if craft.regions else ""),
        skill_band=payload.skill_band,
        material_cost=payload.material_cost,
        quality_score=payload.quality_score,
        gi_tagged=payload.gi_tagged,
        natural_dye=payload.natural_dye,
        channel=payload.channel,
        quantity=payload.quantity,
        artisan_expectation=payload.artisan_expectation,
        labour_cost=payload.labour_cost,
        other_cost=payload.other_cost,
        desired_margin_percent=payload.desired_margin_percent,
    )
    out = rec.to_dict()

    hours = payload.making_hours or (
        payload.making_days * 6 if payload.making_days else craft.labour_hours)
    ml = pricing_ml.predict(
        craft,
        material_cost=payload.material_cost,
        labour_hours=hours,
        skill_band=payload.skill_band,
        complexity=payload.complexity,
        quality_score=payload.quality_score,
        gi_tagged=payload.gi_tagged,
        region=payload.region,
        month=date.today().month,
        channel=payload.channel,
        quantity=payload.quantity,
        natural_dye=payload.natural_dye,
        sustainability=payload.sustainability_score,
    )
    out["ml"] = ml
    out["reconciliation"] = pricing_ml.reconcile(rec.recommended, ml)
    return out


@router.get("/product/{product_id}")
def price_for_product(product_id: str, channel: str = "direct", quantity: int = 1,
                      db: Session = Depends(get_db)) -> dict:
    """Re-price an existing listing — used by the 'is my price still right?' card."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    craft = _resolve_craft(product.ai_meta.get("craft_key"), product.craft_type)
    if not craft:
        raise HTTPException(400, "Cannot resolve the craft for this product")
    meta = product.ai_meta.get("transcript_facts", {}) or {}
    vision = product.ai_meta.get("vision") or {}
    rec = recommend_price(
        craft,
        complexity=vision.get("complexity", 1.0),
        making_days=meta.get("making_days"),
        making_hours=meta.get("making_hours"),
        region=product.region,
        quality_score=product.quality_score,
        gi_tagged=product.gi_tagged,
        channel=channel,
        quantity=quantity,
    )
    out = rec.to_dict()
    out["current_price"] = product.price
    out["delta_percent"] = round(
        (rec.recommended - product.price) / max(product.price, 1) * 100, 1
    )
    return out


@router.get("/crafts")
def crafts() -> dict:
    return {
        "crafts": [
            {
                "key": c.key, "name": c.name, "name_hi": c.name_hi,
                "category": c.category, "material": c.default_material,
                "regions": c.regions, "gi_tagged": c.gi_tagged,
                "skill_band": c.skill_band, "typical_hours": c.labour_hours,
                "material_cost": c.material_cost, "export_demand": c.export_demand,
            }
            for c in CRAFTS
        ]
    }


@router.get("/market-context")
def market_context() -> dict:
    """Season and channel context the pricing screen explains to the artisan."""
    month = date.today().month
    return {
        "month": month,
        "season_label": SEASON_LABEL.get(month, ""),
        "demand_index": SEASON_INDEX.get(month, 1.0),
        "season_curve": [
            {"month": m, "index": SEASON_INDEX[m], "label": SEASON_LABEL[m]}
            for m in range(1, 13)
        ],
        "channels": [
            {"key": k, "margin_percent": round(v * 100, 1)} for k, v in CHANNEL_MARGIN.items()
        ],
    }
