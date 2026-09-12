"""Voice assistant scripts served to the app."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..services import voice_scripts as vs

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/welcome")
def welcome(role: str = "customer", lang: str = "hi") -> dict:
    """The line the app speaks the moment someone opens it."""
    return {
        "role": role,
        "lang": lang,
        "text": vs.welcome(role, lang),
        "text_other": vs.welcome(role, "en" if lang == "hi" else "hi"),
        "tips": vs.tips(role, lang),
    }


@router.get("/script/{screen}")
def script(
    screen: str,
    lang: str = "hi",
    region: str = "",
    hours: str = "",
    missing: str = "",
    tip: str = "",
) -> dict:
    text = vs.screen_script(
        screen, lang, region=region or "India", hours=hours or "kuch",
        missing=missing or "", tip=tip or "",
    )
    return {"screen": screen, "lang": lang, "text": text, "found": bool(text)}


@router.get("/scripts")
def all_scripts(lang: str = "hi") -> dict:
    """Bulk fetch so the app can speak instantly without a round trip."""
    return {
        "lang": lang,
        "welcome": {role: vs.welcome(role, lang) for role in vs.WELCOME},
        "screens": {k: v.get(lang, v.get("en", "")) for k, v in vs.SCREENS.items()},
        "tips": {role: vs.tips(role, lang) for role in vs.TIPS},
    }


@router.get("/roles")
def roles(lang: str = Query("hi")) -> dict:
    """The 'why are you here?' picker shown on first open."""
    return {"roles": vs.ROLES, "prompt": vs.screen_script("role_select", lang)}
