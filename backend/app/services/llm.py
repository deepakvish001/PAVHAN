"""Optional Claude API layer.

PAVHAN is designed to be demo-safe: with no API key it runs entirely on the
deterministic engines in this package. When ANTHROPIC_API_KEY is present the
same call sites route through Claude for richer copy and true multimodal image
understanding, and every response is still validated against the structured
facts we extracted locally — the model may improve wording, it may not invent
a material the artisan never mentioned.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger("pavhan.llm")

LISTING_SYSTEM = """You are the cataloguing assistant inside PAVHAN, a platform \
that helps Indian artisans sell their craft directly.

You will be given (a) structured facts already extracted from the artisan's own \
voice note, (b) measurements taken from their photograph, and (c) reference \
knowledge about the craft.

Rules you must follow:
1. NEVER state a fact the artisan did not say and the photo does not support. \
If a field is unknown, return null for it.
2. Write warmly and concretely. No marketing hyperbole, no "exquisite", no \
"one of a kind" unless the craft genuinely is.
3. The `story` should teach the buyer something true about the technique.
4. Return Hindi copy that a village artisan would recognise as their own words, \
not textbook Hindi.
5. Respond with JSON only, matching the schema given. No prose outside JSON."""


class LLMUnavailable(RuntimeError):
    pass


async def _call_claude(
    messages: list[dict],
    *,
    system: str,
    max_tokens: int = 2000,
    temperature: float = 0.4,
) -> str:
    if not settings.llm_enabled:
        raise LLMUnavailable("ANTHROPIC_API_KEY not configured")
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": messages,
    }
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    url = f"{settings.anthropic_base_url.rstrip('/')}/v1/messages"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    parts = [blk.get("text", "") for blk in data.get("content", []) if blk.get("type") == "text"]
    return "".join(parts).strip()


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model response")
    return json.loads(text[start : end + 1])


async def enrich_listing(
    *,
    facts: dict,
    vision: dict,
    craft: dict,
    image_bytes: bytes | None = None,
    image_media_type: str = "image/jpeg",
) -> dict[str, Any] | None:
    """Ask Claude to improve the listing copy. Returns None if unavailable."""
    if not settings.llm_enabled:
        return None

    schema = {
        "title": "string, max 60 chars, specific not generic",
        "short_description": "string, one sentence, max 140 chars",
        "detailed_description": "string, 3-5 sentences",
        "story": "string, 2-3 sentences about the technique and its place",
        "title_hi": "string, Hindi",
        "short_description_hi": "string, Hindi",
        "tags": ["6-10 short lowercase tags"],
        "seo_keywords": ["6-10 buyer search phrases"],
        "care_instructions": "string or null",
        "suggested_occasions": ["2-4 occasions this suits"],
        "confidence": "integer 0-100, how sure you are of the craft identification",
    }
    content: list[dict] = []
    if image_bytes:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_media_type,
                "data": base64.b64encode(image_bytes).decode(),
            },
        })
    content.append({
        "type": "text",
        "text": (
            "Facts extracted from the artisan's voice note:\n"
            f"{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
            "Measurements taken from the photograph:\n"
            f"{json.dumps(vision, ensure_ascii=False, indent=2)}\n\n"
            "Reference knowledge for the most likely craft:\n"
            f"{json.dumps(craft, ensure_ascii=False, indent=2)}\n\n"
            "Return JSON exactly matching this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}"
        ),
    })
    try:
        raw = await _call_claude(
            [{"role": "user", "content": content}], system=LISTING_SYSTEM
        )
        return _extract_json(raw)
    except Exception as exc:
        log.warning("Claude enrichment unavailable, using on-device engine: %s", exc)
        return None


async def transcribe_audio(audio: bytes, filename: str, language: str = "hi") -> str | None:
    """Server-side speech-to-text fallback when the browser API is blocked."""
    if not settings.whisper_enabled:
        return None
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                settings.whisper_api_url,
                headers={"Authorization": f"Bearer {settings.whisper_api_key}"},
                files={"file": (filename, audio, "audio/webm")},
                data={"model": "whisper-1", "language": language},
            )
            resp.raise_for_status()
            return resp.json().get("text", "").strip()
    except Exception as exc:
        log.warning("Server transcription failed: %s", exc)
        return None


def status() -> dict:
    return {
        "llm": "claude" if settings.llm_enabled else "on-device",
        "llm_model": settings.anthropic_model if settings.llm_enabled else "pavhan-engine-v1",
        "speech_to_text": "whisper" if settings.whisper_enabled else "browser-web-speech",
        "vision": "claude-multimodal" if settings.llm_enabled else "pavhan-colour-science",
    }
