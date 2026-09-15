"""Mobile-OTP sign-in.

An artisan has a phone number and usually no email, so the number is the
identity. This is a prototype implementation: no SMS gateway is wired up, so
the OTP is returned in the response and printed to the server log. That is
clearly marked in the response — the app shows it on screen as a demo hint
rather than pretending an SMS was sent.

Swapping in a real gateway is one function: replace `_deliver`.
"""

from __future__ import annotations

import hashlib
import logging
import random
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import UserOut

log = logging.getLogger("pavhan.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

OTP_TTL_SECONDS = 300
MAX_ATTEMPTS = 5

# phone -> {code, expires, attempts}. In-process on purpose: a prototype
# should not grow a Redis dependency for six digits.
_PENDING: dict[str, dict] = {}
# token -> user_id
_SESSIONS: dict[str, str] = {}


class OtpRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=20)


class OtpVerify(BaseModel):
    phone: str
    code: str
    name: str | None = None
    role: str = "artisan"
    language: str = "hi"


def _normalise(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def _deliver(phone: str, code: str) -> bool:
    """Send the code. Returns True when a real channel was used.

    Wire an SMS provider here and the rest of the flow needs no changes.
    """
    log.info("OTP for %s is %s (no SMS gateway configured)", phone, code)
    return False


@router.post("/request-otp")
def request_otp(payload: OtpRequest, db: Session = Depends(get_db)) -> dict:
    phone = _normalise(payload.phone)
    if len(phone) < 10:
        raise HTTPException(400, "Enter a 10-digit mobile number")

    code = f"{random.randint(0, 999999):06d}"
    _PENDING[phone] = {"code": code, "expires": time.time() + OTP_TTL_SECONDS, "attempts": 0}
    delivered = _deliver(phone, code)

    existing = db.scalars(select(User).where(User.phone.endswith(phone))).first()
    return {
        "phone": phone,
        "sent": True,
        "delivered_by_sms": delivered,
        "expires_in": OTP_TTL_SECONDS,
        "returning_user": bool(existing),
        "name": existing.name if existing else None,
        # Prototype only. With a gateway configured this field disappears.
        "demo_code": None if delivered else code,
        "demo_note": None if delivered else
        "No SMS gateway is configured, so the code is shown here for the demo.",
        "demo_note_hi": None if delivered else
        "एसएमएस सेवा जुड़ी नहीं है, इसलिए डेमो के लिए कोड यहीं दिखाया गया है।",
    }


@router.post("/verify-otp")
def verify_otp(payload: OtpVerify, db: Session = Depends(get_db)) -> dict:
    phone = _normalise(payload.phone)
    pending = _PENDING.get(phone)
    if not pending:
        raise HTTPException(400, "Request a code first")
    if time.time() > pending["expires"]:
        _PENDING.pop(phone, None)
        raise HTTPException(400, "That code has expired. Ask for a new one.")

    pending["attempts"] += 1
    if pending["attempts"] > MAX_ATTEMPTS:
        _PENDING.pop(phone, None)
        raise HTTPException(429, "Too many wrong attempts. Ask for a new code.")
    if payload.code.strip() != pending["code"]:
        left = MAX_ATTEMPTS - pending["attempts"]
        raise HTTPException(400, f"Wrong code. {left} attempt(s) left.")

    _PENDING.pop(phone, None)

    user = db.scalars(select(User).where(User.phone.endswith(phone))).first()
    created = False
    if not user:
        user = User(
            name=payload.name or "PAVHAN user",
            phone=f"+91 {phone}",
            role=payload.role,
            language=payload.language,
            avatar="🧑‍🎨" if payload.role == "artisan" else "🛍️",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        created = True

    token = secrets.token_urlsafe(24)
    _SESSIONS[token] = user.id
    return {
        "token": token,
        "created": created,
        "needs_onboarding": created or not user.craft_focus,
        "user": UserOut.model_validate(user).model_dump(),
    }


class ProfileSetup(BaseModel):
    token: str
    name: str | None = None
    craft_focus: str | None = None
    region: str | None = None
    language: str | None = None
    experience_years: int | None = None
    role: str | None = None


@router.post("/complete-profile", response_model=UserOut)
def complete_profile(payload: ProfileSetup, db: Session = Depends(get_db)) -> User:
    user_id = _SESSIONS.get(payload.token)
    if not user_id:
        raise HTTPException(401, "Sign in again")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    for field in ("name", "craft_focus", "region", "language", "experience_years", "role"):
        value = getattr(payload, field)
        if value not in (None, ""):
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
def me(token: str, db: Session = Depends(get_db)) -> User:
    user_id = _SESSIONS.get(token)
    if not user_id:
        raise HTTPException(401, "Sign in again")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/logout")
def logout(token: str) -> dict:
    _SESSIONS.pop(token, None)
    return {"ok": True}
