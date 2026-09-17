"""PAVHAN API — AI-Powered Growth for Artisan Craft."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import MEDIA_DIR, settings
from .database import Base, SessionLocal, engine, sync_columns
from .routers import (
    ai, assistant, auth, buyers, collective, export, fairs, impact, logistics,
    payments, pricing, products, search, share, studio, trade, users, voice,
)
from .seed import seed
from .services import llm, search_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pavhan")

SEED_MEDIA_DIR = Path(__file__).resolve().parent.parent / "seed_media"
# Built single-page app. When it exists, this one server hosts everything, so
# the whole demo runs on http://localhost:8000 — which matters beyond
# convenience: the microphone and speech APIs are disabled by browsers on any
# origin that is neither localhost nor https.
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Anyone upgrading from an earlier version has the old table shape on
    # disk. Add what is missing rather than greeting them with "no such
    # column: users.upi_vpa".
    added = sync_columns(Base)
    if added:
        log.info("Added %d new column(s) to the existing database: %s",
                 len(added), ", ".join(added))
    with SessionLocal() as db:
        result = seed(db)
        if result.get("seeded"):
            log.info("Seeded catalogue: %s", result)
        products.reindex(db)
        log.info("Search index built over %d listings", len(search_engine.index.docs))
    log.info("Engines: %s", llm.status())
    yield


app = FastAPI(
    title="PAVHAN API",
    description=(
        "AI-Powered Growth for Artisan Craft.\n\n"
        "Voice + photo in, a complete priced listing and matched buyers out.\n\n"
        "Every AI endpoint works with no API key configured — the on-device "
        "engines (colour-science vision, Hinglish NLP, explainable pricing) are "
        "the default path, and Claude is layered on top when a key is present."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (products.router, search.router, ai.router, studio.router,
               pricing.router, buyers.router, voice.router, users.router,
               assistant.router, auth.router, export.router,
               impact.router, fairs.router, trade.router,
               payments.router, logistics.router, collective.router,
               share.router):
    app.include_router(router)

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
if SEED_MEDIA_DIR.exists():
    app.mount("/seed", StaticFiles(directory=SEED_MEDIA_DIR), name="seed")


if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")
    log.info("Serving the built app from %s", DIST_DIR)


@app.get("/", include_in_schema=False)
def root():
    """The app when it has been built, the API docs otherwise."""
    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return RedirectResponse("/docs")


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "tagline": settings.tagline,
        "version": __version__,
        "engines": llm.status(),
        "indexed_listings": len(search_engine.index.docs),
    }


# Files the browser insists on finding at the site root. The service worker in
# particular is scoped to the directory it is served from, so /sw.js is the
# only path that lets it control the whole app.
ROOT_FILES = {
    "sw.js": "application/javascript",
    "manifest.webmanifest": "application/manifest+json",
    "icon.svg": "image/svg+xml",
    "favicon.ico": "image/x-icon",
    "robots.txt": "text/plain",
}


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """Client-side routes (/artisan, /product/abc) must return the app shell.

    Registered last so it never shadows /api, /docs, /media or /seed.
    """
    if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "media/", "seed/", "assets/")):
        raise HTTPException(404, "Not found")

    if full_path in ROOT_FILES:
        asset = DIST_DIR / full_path
        if asset.exists():
            return FileResponse(
                asset,
                media_type=ROOT_FILES[full_path],
                # The worker must be allowed to update, or an artisan stays on
                # a stale build forever.
                headers={"Cache-Control": "no-cache"} if full_path == "sw.js" else None,
            )
        raise HTTPException(404, "Not found")

    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return RedirectResponse("/docs")


@app.post("/api/admin/reseed", tags=["meta"])
def reseed() -> dict:
    """Reset the demo catalogue. Handy right before a presentation."""
    with SessionLocal() as db:
        result = seed(db, force=True)
        products.reindex(db)
    return result
