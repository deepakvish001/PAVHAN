"""PAVHAN API — AI-Powered Growth for Artisan Craft."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import MEDIA_DIR, settings
from .database import Base, SessionLocal, engine
from .routers import ai, buyers, pricing, products, search, users, voice
from .seed import seed
from .services import llm, search_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pavhan")

SEED_MEDIA_DIR = Path(__file__).resolve().parent.parent / "seed_media"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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

for router in (products.router, search.router, ai.router, pricing.router,
               buyers.router, voice.router, users.router):
    app.include_router(router)

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
if SEED_MEDIA_DIR.exists():
    app.mount("/seed", StaticFiles(directory=SEED_MEDIA_DIR), name="seed")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
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


@app.post("/api/admin/reseed", tags=["meta"])
def reseed() -> dict:
    """Reset the demo catalogue. Handy right before a presentation."""
    with SessionLocal() as db:
        result = seed(db, force=True)
        products.reindex(db)
    return result
