"""Booking a despatch, and tracking it.

Rates and serviceability come from `services/logistics`; this router's job is
to attach that to a real order, keep the shipment's status and the order's
status honest with each other, and never offer the artisan a carrier that does
not come to their village.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Product, Shipment, User
from ..services import logistics as lg
from ..services import share

router = APIRouter(prefix="/api/logistics", tags=["logistics"])

# Roughly what a piece of each category weighs, packed. Used when the artisan
# never stated a weight, so a quote can still be given rather than a form.
CATEGORY_WEIGHT_G = {
    "Textiles": 600, "Pottery": 1400, "Metalwork": 1100, "Woodwork": 900,
    "Jewellery": 200, "Painting": 500, "Basketry": 700,
}
DEFAULT_WEIGHT_G = 700


class BookIn(BaseModel):
    carrier: str
    to_pincode: str
    weight_g: int = 0
    from_pincode: str = ""


def _weight_for(product: Product | None, quantity: int) -> int:
    """Parse the artisan's own stated weight, else fall back on the category.

    Weights arrive as free text — "800 gram", "1.2 kg", "approx 450g" — because
    they were spoken, not typed into a number field.
    """
    grams = 0
    raw = (product.weight if product else "") or ""
    digits = "".join(ch if (ch.isdigit() or ch == ".") else " " for ch in raw).split()
    value = next((float(d) for d in digits if d.replace(".", "", 1).isdigit()), 0.0)
    if value:
        lowered = raw.lower()
        grams = int(value * 1000) if ("kg" in lowered or "किलो" in raw) else int(value)
    if grams <= 0:
        grams = CATEGORY_WEIGHT_G.get(
            product.category if product else "", DEFAULT_WEIGHT_G)
    return max(100, grams * max(1, quantity))


@router.get("/pincode/{pincode}")
def pincode(pincode: str) -> dict:
    """Where is this, and do private couriers bother going there?"""
    found = lg.locate(pincode)
    if found.get("valid") and found["remote"]:
        found["note"] = ("Private couriers are unreliable here. India Post "
                         "reaches it.")
        found["note_hi"] = ("यहाँ निजी कूरियर भरोसेमंद नहीं। इंडिया पोस्ट "
                            "पहुँचता है।")
    return found


@router.get("/quote")
def rate_quote(origin: str = Query(...), destination: str = Query(...),
               weight_g: int = Query(700), category: str = Query("")) -> dict:
    return lg.quote(origin=origin, destination=destination,
                    weight_g=weight_g, category=category)


@router.get("/order/{order_id}/options")
def order_options(order_id: str, to_pincode: str = Query(""),
                  db: Session = Depends(get_db)) -> dict:
    """Carrier options for a real order, with the weight worked out for them."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    product = db.get(Product, order.product_id)
    artisan = db.get(User, product.artisan_id) if product and product.artisan_id else None

    origin = (artisan.pincode if artisan else "") or ""
    if not origin:
        return {"serviceable": False,
                "reason": "Add your pincode in Profile so carriers can quote a rate",
                "reason_hi": "प्रोफ़ाइल में अपना पिनकोड डालें ताकि दर मिल सके",
                "needs_origin": True}
    if not to_pincode:
        return {"serviceable": False,
                "reason": "Enter the delivery pincode",
                "reason_hi": "डिलीवरी का पिनकोड डालें",
                "needs_destination": True, "from_pincode": origin}

    weight = _weight_for(product, order.quantity)
    body = lg.quote(origin=origin, destination=to_pincode, weight_g=weight,
                    category=product.category if product else "")
    body["from_pincode"] = origin
    body["quantity"] = order.quantity
    body["weight_basis"] = (
        f"{order.quantity} x {weight // max(1, order.quantity)}g"
        if order.quantity > 1 else f"{weight}g")
    existing = db.scalars(select(Shipment).where(
        Shipment.order_id == order_id)).first()
    body["already_booked"] = bool(existing)
    return body


@router.post("/order/{order_id}/book", status_code=201)
def book(order_id: str, payload: BookIn, db: Session = Depends(get_db)) -> dict:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if db.scalars(select(Shipment).where(Shipment.order_id == order_id)).first():
        raise HTTPException(409, "This order already has a shipment")

    product = db.get(Product, order.product_id)
    artisan = db.get(User, product.artisan_id) if product and product.artisan_id else None
    origin = payload.from_pincode or (artisan.pincode if artisan else "")
    if not origin:
        raise HTTPException(400, "Add your pincode in Profile first")

    weight = payload.weight_g or _weight_for(product, order.quantity)
    options = lg.quote(origin=origin, destination=payload.to_pincode,
                       weight_g=weight,
                       category=product.category if product else "")
    if not options.get("serviceable"):
        raise HTTPException(400, options.get("reason", "Not serviceable"))

    chosen = next((o for o in options["options"] if o["carrier"] == payload.carrier), None)
    if not chosen:
        raise HTTPException(
            400, f"{payload.carrier} does not deliver to that pincode")

    now = datetime.now(timezone.utc)
    pickup = lg.pickup_window(now)
    shipment = Shipment(
        order_id=order.id, carrier=chosen["carrier"], service=chosen["name"],
        from_pincode=origin, to_pincode=payload.to_pincode,
        weight_g=weight, zone=options["zone"], rate=chosen["total"],
        promised_days=chosen["days"], awb=lg.new_awb(chosen["carrier"]),
        status="booked", pickup_on=pickup,
        timeline=[{"status": "booked", "at": now.isoformat(),
                   "note": f"{chosen['name']}, pickup {pickup:%d %b, 11am}"}],
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    return {
        "shipment": _shipment_out(shipment),
        "whatsapp_to_buyer": share.wa_link("", share.shipment_booked(
            carrier=chosen["name"], awb=shipment.awb, days=chosen["days"])),
    }


def _shipment_out(s: Shipment) -> dict:
    label, label_hi = lg.STAGE_LABELS.get(s.status, (s.status, s.status))
    stage_keys = [k for k, _, _ in lg.TRACK_STAGES]
    return {
        "id": s.id, "order_id": s.order_id, "carrier": s.carrier,
        "service": s.service, "awb": s.awb, "rate": s.rate,
        "weight_g": s.weight_g, "zone": s.zone,
        "from_pincode": s.from_pincode, "to_pincode": s.to_pincode,
        "promised_days": s.promised_days,
        "status": s.status, "status_label": label, "status_label_hi": label_hi,
        "stage_index": stage_keys.index(s.status) if s.status in stage_keys else 0,
        "stages": [{"key": k, "label": en, "label_hi": hi}
                   for k, en, hi in lg.TRACK_STAGES],
        "pickup_on": s.pickup_on, "timeline": s.timeline or [],
        "created_at": s.created_at,
    }


@router.get("/order/{order_id}/shipment")
def order_shipment(order_id: str, db: Session = Depends(get_db)) -> dict:
    """Has this order been despatched yet?

    A null answer rather than a 404, because "not yet" is the ordinary case
    and the despatch screen asks this every time it opens. A 404 here forced
    the caller into `catch(() => null)`, which swallows a genuine network
    failure just as happily as it swallows the expected miss — and fills the
    console with red that hides the errors that do matter.
    """
    s = db.scalars(select(Shipment).where(Shipment.order_id == order_id)).first()
    return {"shipment": _shipment_out(s) if s else None}


@router.get("/track/{awb}")
def track(awb: str, db: Session = Depends(get_db)) -> dict:
    """Tracking by AWB alone, so it works for a buyer with no account."""
    s = db.scalars(select(Shipment).where(Shipment.awb == awb)).first()
    if not s:
        raise HTTPException(404, "No shipment with that tracking number")
    return _shipment_out(s)


@router.post("/shipment/{shipment_id}/advance")
def advance(shipment_id: str, to: str = Query(...),
            db: Session = Depends(get_db)) -> dict:
    """Move a shipment on, and keep the order's own status in step.

    The two used to be able to disagree — an order marked delivered whose
    parcel was still in transit — which is exactly the contradiction a buyer
    screenshots.
    """
    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")
    keys = [k for k, _, _ in lg.TRACK_STAGES]
    if to not in keys:
        raise HTTPException(400, f"Status must be one of {keys}")
    if keys.index(to) < keys.index(s.status):
        raise HTTPException(409, "A shipment cannot move backwards")

    now = datetime.now(timezone.utc)
    s.status = to
    label = lg.STAGE_LABELS[to][0]
    s.timeline = list(s.timeline or []) + [
        {"status": to, "at": now.isoformat(), "note": label}]

    order = db.get(Order, s.order_id)
    if order:
        if to in ("picked_up", "in_transit", "out_for_delivery") and \
                order.status in ("placed", "accepted", "in_production"):
            order.status = "shipped"
            order.timeline = list(order.timeline or []) + [
                {"stage": "shipped", "at": now.isoformat(),
                 "note": f"{s.service}, {s.awb}"}]
        elif to == "delivered" and order.status != "delivered":
            order.status = "delivered"
            order.timeline = list(order.timeline or []) + [
                {"stage": "delivered", "at": now.isoformat(),
                 "note": f"Delivered by {s.service}"}]

    db.commit()
    db.refresh(s)
    return {"shipment": _shipment_out(s),
            "order_status": order.status if order else None}
