"""Paying for an order, and the artisan watching the money arrive.

The states here are the ones an artisan asks about in conversation — has the
buyer paid, is it still being held, has it reached me — rather than the ones a
payment processor uses internally. Everything the screen shows is derived from
a Payment row, so the artisan's earnings page and the buyer's receipt cannot
tell two different stories.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Payment, Product, User
from ..services import payments as pay
from ..services import share

router = APIRouter(prefix="/api/payments", tags=["payments"])


class VpaIn(BaseModel):
    vpa: str
    payout_name: str = ""


class IntentIn(BaseModel):
    method: str = "upi"
    payer_name: str = ""


class ConfirmIn(BaseModel):
    reference: str
    payer_name: str = ""


def _artisan_for(order: Order, db: Session) -> User | None:
    product = db.get(Product, order.product_id)
    return db.get(User, product.artisan_id) if product and product.artisan_id else None


def _payment_out(p: Payment, order: Order | None, artisan: User | None,
                 product: Product | None) -> dict:
    out = {
        "id": p.id, "order_id": p.order_id,
        "amount": p.amount, "platform_fee": p.platform_fee,
        "artisan_amount": p.artisan_amount,
        "method": p.method, "reference": p.reference,
        "payer_name": p.payer_name, "payee_vpa": p.payee_vpa,
        "timeline": p.timeline or [],
        "created_at": p.created_at,
        "held_at": p.held_at, "released_at": p.released_at,
        **pay.describe(p.state),
    }
    if p.state == "awaiting_payment" and p.method == "upi" and p.payee_vpa:
        title = product.title if product else "PAVHAN order"
        out["upi_link"] = pay.upi_link(
            vpa=p.payee_vpa,
            name=(artisan.payout_name or artisan.name) if artisan else "PAVHAN artisan",
            amount=p.amount,
            note=f"PAVHAN {title}"[:80],
            reference=p.reference,
        )
        out["whatsapp"] = share.wa_link("", share.payment_request(
            artisan_name=artisan.name if artisan else "the artisan",
            amount=p.amount, upi_link_url=out["upi_link"],
            product_title=title, lang="en"))
    # What could happen next, so the screen never offers a dead button.
    out["next_states"] = sorted(pay.TRANSITIONS.get(p.state, set()))
    return out


# ------------------------------------------------------------------- the VPA
@router.get("/check-vpa")
def check_vpa(vpa: str = Query("")) -> dict:
    """Runs while the artisan is still typing, so it judges rather than raises."""
    return pay.check_vpa(vpa)


@router.post("/artisan/{artisan_id}/vpa")
def set_vpa(artisan_id: str, payload: VpaIn, db: Session = Depends(get_db)) -> dict:
    artisan = db.get(User, artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")
    verdict = pay.check_vpa(payload.vpa)
    if not verdict.get("valid"):
        raise HTTPException(400, verdict.get("reason", "That is not a UPI ID"))
    artisan.upi_vpa = verdict["vpa"]
    artisan.payout_name = (payload.payout_name or artisan.payout_name
                           or artisan.name)
    db.commit()
    return {"saved": True, "upi_vpa": artisan.upi_vpa,
            "payout_name": artisan.payout_name, **verdict}


# ------------------------------------------------------------------ payments
@router.get("/order/{order_id}")
def order_payment(order_id: str, db: Session = Depends(get_db)) -> dict:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    artisan = _artisan_for(order, db)
    product = db.get(Product, order.product_id)
    payment = db.scalars(select(Payment).where(
        Payment.order_id == order_id).order_by(Payment.created_at.desc())).first()

    body = {
        "order": {"id": order.id, "status": order.status,
                  "amount": order.amount, "quantity": order.quantity,
                  "customer_name": order.customer_name},
        "split": pay.split(order.amount),
        "disclaimer": pay.DISCLAIMER,
        "artisan_vpa": artisan.upi_vpa if artisan else "",
        "vpa_missing": not (artisan and artisan.upi_vpa),
    }
    body["payment"] = _payment_out(payment, order, artisan, product) if payment else None
    return body


@router.post("/order/{order_id}/intent", status_code=201)
def create_intent(order_id: str, payload: IntentIn,
                  db: Session = Depends(get_db)) -> dict:
    """Raise a payment for an order — the link the buyer actually taps."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if payload.method not in ("upi", "cod", "bank"):
        raise HTTPException(400, "Method must be upi, cod or bank")

    artisan = _artisan_for(order, db)
    if payload.method == "upi" and not (artisan and artisan.upi_vpa):
        # Refusing here is the point. A payment link with no destination
        # collects money into nowhere, and the artisan finds out last.
        raise HTTPException(
            400, "This artisan has not added a UPI ID yet, so there is nowhere "
                 "to send the money. Add it in Profile first.")

    existing = db.scalars(select(Payment).where(
        Payment.order_id == order_id,
        Payment.state.in_(["awaiting_payment", "held"]))).first()
    if existing:
        raise HTTPException(409, "This order already has a live payment")

    breakdown = pay.split(order.amount)
    now = datetime.now(timezone.utc)
    payment = Payment(
        order_id=order.id,
        artisan_id=artisan.id if artisan else "",
        amount=breakdown["amount"],
        platform_fee=breakdown["platform_fee"],
        artisan_amount=breakdown["artisan_amount"],
        method=payload.method,
        state="awaiting_payment",
        payer_name=payload.payer_name or order.customer_name,
        payee_vpa=artisan.upi_vpa if artisan else "",
        reference=pay.reference_for(order.id),
        timeline=[{"state": "awaiting_payment", "at": now.isoformat(),
                   "note": f"Payment raised for Rs.{breakdown['amount']:,.0f}"}],
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    product = db.get(Product, order.product_id)
    return {"payment": _payment_out(payment, order, artisan, product),
            "split": breakdown, "disclaimer": pay.DISCLAIMER}


@router.post("/{payment_id}/confirm")
def confirm(payment_id: str, payload: ConfirmIn,
            db: Session = Depends(get_db)) -> dict:
    """The buyer has paid; record the UTR their own UPI app showed them.

    In production this is a provider webhook. It is a typed reference here,
    and the screen says so — an unverifiable confirmation dressed up as a
    verified one would be the dishonest version of this feature.
    """
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    if not pay.can_transition(payment.state, "held"):
        raise HTTPException(409, f"A payment that is '{payment.state}' cannot be confirmed")
    reference = (payload.reference or "").strip()
    if len(reference) < 6:
        raise HTTPException(400, "Enter the UTR or reference number from your payment app")

    now = datetime.now(timezone.utc)
    payment.state = "held"
    payment.held_at = now
    payment.reference = reference
    if payload.payer_name:
        payment.payer_name = payload.payer_name
    payment.timeline = list(payment.timeline or []) + [{
        "state": "held", "at": now.isoformat(),
        "note": f"Paid, reference {reference}. Held until delivery."}]
    db.commit()
    db.refresh(payment)

    order = db.get(Order, payment.order_id)
    artisan = _artisan_for(order, db) if order else None
    return {
        "payment": _payment_out(payment, order, artisan,
                                db.get(Product, order.product_id) if order else None),
        "whatsapp_to_artisan": share.wa_link(
            artisan.phone if artisan else "",
            share.payment_received(amount=payment.artisan_amount,
                                   reference=reference, lang="hi")),
    }


@router.post("/{payment_id}/release")
def release(payment_id: str, db: Session = Depends(get_db)) -> dict:
    """Delivery happened, so the held money goes to the artisan."""
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    if not pay.can_transition(payment.state, "released"):
        raise HTTPException(409, f"A payment that is '{payment.state}' cannot be released")

    order = db.get(Order, payment.order_id)
    if order and order.status != "delivered":
        # The hold is the buyer's protection. Releasing before delivery would
        # quietly remove it while still telling them it was there.
        raise HTTPException(
            409, "The money is held until the order is delivered. Mark the "
                 "order delivered first.")

    now = datetime.now(timezone.utc)
    payment.state = "released"
    payment.released_at = now
    payment.timeline = list(payment.timeline or []) + [{
        "state": "released", "at": now.isoformat(),
        "note": f"Rs.{payment.artisan_amount:,.0f} released to {payment.payee_vpa}"}]
    db.commit()
    db.refresh(payment)
    artisan = _artisan_for(order, db) if order else None
    return {"payment": _payment_out(payment, order, artisan,
                                    db.get(Product, order.product_id) if order else None)}


@router.post("/{payment_id}/refund")
def refund(payment_id: str, db: Session = Depends(get_db)) -> dict:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    if not pay.can_transition(payment.state, "refunded"):
        raise HTTPException(409, f"A payment that is '{payment.state}' cannot be refunded")
    now = datetime.now(timezone.utc)
    payment.state = "refunded"
    payment.timeline = list(payment.timeline or []) + [{
        "state": "refunded", "at": now.isoformat(),
        "note": "Returned to the buyer"}]
    db.commit()
    db.refresh(payment)
    return {"payment": _payment_out(payment, db.get(Order, payment.order_id), None, None)}


# ------------------------------------------------------------- the statement
@router.get("/artisan/{artisan_id}")
def statement(artisan_id: str, db: Session = Depends(get_db)) -> dict:
    """What has reached this artisan, what is on the way, and what it replaced."""
    artisan = db.get(User, artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")

    rows = list(db.scalars(select(Payment).where(
        Payment.artisan_id == artisan_id).order_by(Payment.created_at.desc())))

    received = sum(p.artisan_amount for p in rows if p.state == "released")
    held = sum(p.artisan_amount for p in rows if p.state == "held")
    awaiting = sum(p.artisan_amount for p in rows if p.state == "awaiting_payment")
    gross = sum(p.amount for p in rows if p.state in ("held", "released"))
    middleman = gross * pay.MIDDLEMAN_SHARE

    out = []
    for p in rows:
        order = db.get(Order, p.order_id)
        product = db.get(Product, order.product_id) if order else None
        out.append({
            "id": p.id, "order_id": p.order_id,
            "amount": p.amount, "artisan_amount": p.artisan_amount,
            "platform_fee": p.platform_fee,
            "method": p.method, "reference": p.reference,
            "created_at": p.created_at, "released_at": p.released_at,
            "product_title": product.title if product else "",
            **pay.describe(p.state),
        })

    return {
        "artisan": {"id": artisan.id, "name": artisan.name,
                    "upi_vpa": artisan.upi_vpa,
                    "payout_name": artisan.payout_name},
        "payments": out,
        "summary": {
            "received": round(received, 2),
            "held": round(held, 2),
            "awaiting": round(awaiting, 2),
            "gross": round(gross, 2),
            "platform_fees": round(sum(p.platform_fee for p in rows
                                       if p.state in ("held", "released")), 2),
            "middleman_would_have_paid": round(middleman, 2),
            "extra_vs_middleman": round((received + held) - middleman, 2),
            "count": len(rows),
        },
        "disclaimer": pay.DISCLAIMER,
    }
