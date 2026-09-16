"""AI endpoints: image understanding, listing generation, transcription."""

from __future__ import annotations

import time
import uuid
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..config import MEDIA_DIR, settings
from ..services import llm, nlp, pricing_ml
from ..services.listing import build_listing, merge_llm
from ..services.pricing import recommend_price
from ..services.taxonomy import CATEGORIES, CRAFTS, MATERIALS
from ..services.vision import analyse_image

router = APIRouter(prefix="/api/ai", tags=["ai"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/jpg"}
MAX_IMAGE_BYTES = 12 * 1024 * 1024

# Uploaded originals are kept only for the duration of the session so the
# listing step can re-read them for multimodal enrichment.
_IMAGE_CACHE: dict[str, dict] = {}


@router.get("/status")
def ai_status() -> dict:
    """Which engines are actually live right now — shown in the app header."""
    return {
        "app": settings.app_name,
        "tagline": settings.tagline,
        **llm.status(),
        "crafts_known": len(CRAFTS),
        "categories": CATEGORIES,
        "materials": MATERIALS,
    }


@router.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)) -> dict:
    """Read the photograph and return measurements plus photo coaching."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, f"Unsupported image type: {file.content_type}")
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image is larger than 12 MB")
    if not data:
        raise HTTPException(400, "Empty file")

    started = time.perf_counter()
    reading = analyse_image(data)
    if not reading.ok:
        raise HTTPException(400, reading.note or "Could not read that image")

    image_id = uuid.uuid4().hex[:12]
    suffix = {"image/png": ".png", "image/webp": ".webp"}.get(file.content_type, ".jpg")
    path = MEDIA_DIR / f"{image_id}{suffix}"
    path.write_bytes(data)
    _IMAGE_CACHE[image_id] = {"path": str(path), "media_type": file.content_type}

    return {
        "image_id": image_id,
        "url": f"/media/{path.name}",
        "vision": reading.to_dict(),
        "took_ms": round((time.perf_counter() - started) * 1000, 1),
    }


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...), language: str = Form("hi")
) -> dict:
    """Server-side speech-to-text, used when the browser API is unavailable."""
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty audio")
    text = await llm.transcribe_audio(data, file.filename or "audio.webm", language)
    if text is None:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Server transcription is not configured on this deployment. "
                          "Use the in-browser microphone, or type the description.",
                "engine": "unavailable",
            },
        )
    return {"transcript": text, "engine": "whisper", "language": language}


@router.post("/generate-listing")
async def generate_listing(
    transcript: str = Form(""),
    image_id: str | None = Form(None),
    language: str = Form("hi"),
    use_llm: bool = Form(True),
) -> dict:
    """Fuse voice + photo into a full listing, then price it."""
    started = time.perf_counter()
    if not transcript.strip() and not image_id:
        raise HTTPException(
            400,
            "Nothing to work from. Record a voice description or upload a photo first.",
        )

    vision = None
    image_bytes = None
    media_type = "image/jpeg"
    image_url = None
    if image_id:
        from pathlib import Path

        path: Path | None = None
        cached = _IMAGE_CACHE.get(image_id)
        if cached and Path(cached["path"]).exists():
            path = Path(cached["path"])
            media_type = cached["media_type"]
        else:
            # The AI Product Studio writes "<id>_after.<ext>". A listing should
            # carry the cleaned-up photograph, not the raw snapshot, so look
            # for the studio output before giving up on the id.
            for candidate in sorted(MEDIA_DIR.glob(f"{image_id}_after.*")):
                path = candidate
                media_type = "image/png" if candidate.suffix == ".png" else "image/jpeg"
                break

        if path and path.exists():
            image_bytes = path.read_bytes()
            image_url = f"/media/{path.name}"
            vision = analyse_image(image_bytes)

    listing = build_listing(transcript, vision, language=language)
    facts: nlp.TranscriptFacts = listing.pop("_facts")
    craft = listing.pop("_craft")

    if use_llm and settings.llm_enabled:
        enriched = await llm.enrich_listing(
            facts=listing["ai_meta"]["transcript_facts"],
            vision=listing["ai_meta"].get("vision") or {},
            craft={
                "name": craft.name, "category": craft.category,
                "regions": craft.regions, "technique_note": craft.story_hook,
                "gi_tagged": craft.gi_tagged,
            },
            image_bytes=image_bytes,
            image_media_type=media_type,
        )
        listing = merge_llm(listing, enriched)

    price = recommend_price(
        craft,
        complexity=vision.complexity if vision and vision.ok else 1.0,
        making_days=facts.making_days,
        making_hours=facts.making_hours,
        region=listing.get("region", ""),
        quality_score=listing["quality_score"],
        gi_tagged=listing["gi_tagged"],
        natural_dye=facts.mentions_natural_dye,
        artisan_expectation=facts.expected_price,
    )

    listing["images"] = [image_url] if image_url else []
    listing["price"] = price.recommended
    listing["price_floor"] = price.floor
    listing["price_premium"] = price.premium
    pricing_meta = price.to_dict()
    # The listing screen shows the arithmetic; the price screen shows both
    # engines, so the ML view has to travel with the listing.
    ml = pricing_ml.predict(
        craft,
        material_cost=None,
        labour_hours=facts.making_hours or (
            facts.making_days * 6 if facts.making_days else craft.labour_hours),
        complexity=vision.complexity if vision and vision.ok else 1.3,
        quality_score=listing["quality_score"],
        gi_tagged=listing["gi_tagged"],
        region=listing.get("region", ""),
        month=date.today().month,
        natural_dye=facts.mentions_natural_dye,
        sustainability=listing["sustainability_score"],
    )
    pricing_meta["ml"] = ml
    pricing_meta["reconciliation"] = pricing_ml.reconcile(price.recommended, ml)
    listing["pricing_meta"] = pricing_meta
    listing["lead_time_days"] = max(
        3, int((facts.making_days or (facts.making_hours or craft.labour_hours) / 6) + 2)
    )
    listing["moq"] = 1
    listing["took_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return listing


@router.post("/coach")
def coach(transcript: str = Form(""), language: str = Form("hi")) -> dict:
    """Live coaching while the artisan is still speaking."""
    facts = nlp.extract(transcript, hint=language)
    prompts_hi = {
        "material": "यह किस चीज़ से बना है? जैसे रेशम, मिट्टी, लकड़ी।",
        "colour": "इसका मुख्य रंग कौन सा है?",
        "size": "यह कितना बड़ा है? नाप बता दीजिए।",
        "making time": "इसे बनाने में कितने दिन लगे?",
        "place of origin": "आप किस गाँव या शहर से हैं?",
    }
    prompts_en = {
        "material": "What is it made of? Silk, clay, wood?",
        "colour": "What is the main colour?",
        "size": "How big is it? Give the measurement.",
        "making time": "How many days did it take to make?",
        "place of origin": "Which town or district are you from?",
    }
    # Coaching prompts exist in Hindi and English; a Tamil speaker gets the
    # Hindi prompt only if they chose Hindi, otherwise English.
    prompts = prompts_hi if language == "hi" else prompts_en
    return {
        "completeness": facts.completeness,
        "missing_fields": facts.missing_fields,
        "next_question": prompts.get(facts.missing_fields[0]) if facts.missing_fields else None,
        "spoken_language": facts.language,
        "captured": {
            "materials": facts.materials, "colours": facts.colours,
            "size": facts.size, "weight": facts.weight,
            "making_days": facts.making_days, "regions": facts.regions,
            "product": facts.product_noun,
        },
    }
