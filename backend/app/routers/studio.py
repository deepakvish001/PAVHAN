"""AI Product Studio endpoints — the photo half of the problem statement."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import MEDIA_DIR
from ..services.image_studio import HAS_CV2, OUTPUT_SIZE, enhance
from ..services.vision import analyse_image

router = APIRouter(prefix="/api/studio", tags=["studio"])

ALLOWED = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"}
MAX_BYTES = 14 * 1024 * 1024
BACKGROUNDS = {"white", "studio", "transparent", "original"}


@router.get("/status")
def status() -> dict:
    return {
        "engine": "opencv-grabcut" if HAS_CV2 else "numpy-fallback",
        "backgrounds": sorted(BACKGROUNDS),
        "output_size": OUTPUT_SIZE,
        "offline": True,
    }


@router.post("/enhance")
async def enhance_photo(
    file: UploadFile = File(...),
    background: str = Form("white"),
) -> dict:
    """Take a phone snapshot, return an e-commerce-grade product photo.

    Both images are saved so the app can show a real before/after rather than
    asking the artisan to take our word for it.
    """
    if file.content_type not in ALLOWED:
        raise HTTPException(415, f"Unsupported image type: {file.content_type}")
    if background not in BACKGROUNDS:
        raise HTTPException(400, f"background must be one of {sorted(BACKGROUNDS)}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image is larger than 14 MB")

    started = time.perf_counter()
    before_bytes, after_bytes, report = enhance(
        data, background=background, remove_background=background != "original",
    )
    if not report.ok:
        raise HTTPException(400, report.note or "Could not process that image")

    stem = uuid.uuid4().hex[:12]
    suffix = ".png" if background == "transparent" else ".jpg"
    before_path = MEDIA_DIR / f"{stem}_before.jpg"
    after_path = MEDIA_DIR / f"{stem}_after{suffix}"
    before_path.write_bytes(before_bytes)
    after_path.write_bytes(after_bytes)

    # The catalogue engine still wants its own reading of the ENHANCED photo —
    # colour and intricacy measured after correction describe the product more
    # faithfully than measurements taken through a tungsten colour cast.
    reading = analyse_image(after_bytes)

    return {
        "image_id": stem,
        "before_url": f"/media/{before_path.name}",
        "after_url": f"/media/{after_path.name}",
        "background": background,
        "report": report.to_dict(),
        "vision": reading.to_dict() if reading.ok else None,
        "took_ms": round((time.perf_counter() - started) * 1000, 1),
    }
