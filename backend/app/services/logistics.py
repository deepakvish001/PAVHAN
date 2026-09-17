"""Getting the piece out of the village.

An order that reaches a status called "shipped" with nothing behind it is a
label, not a despatch. This module is what makes that status mean something:
which carrier will come to this pincode, what it costs at this weight, how
long it takes, and an AWB the artisan can quote when the buyer asks.

The design decision worth defending is **India Post first**.

Private couriers are faster and their APIs are nicer, and they do not go to
Bhadohi's villages, to most of Kutch, or anywhere in the North-East outside a
few district towns. An artisan in Madhubani whose only listed carrier is
Bluedart has a catalogue and no way to ship from it. India Post reaches every
pincode in the country because it is obliged to, which makes it the only
carrier this app can promise. The private options are offered where they
actually serve, and the screen says which is which.

Rates are the published indicative slabs plus GST, and are labelled as
indicative everywhere they are shown. Booking here reserves and records a
despatch; handing it to the carrier's own API is a credential away, exactly as
with the government marketplaces, and the app says so rather than implying an
integration it does not have.
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone

# ------------------------------------------------------------------ pincodes
#
# First three digits of a PIN identify a postal district, and their ranges map
# onto states. Narrower ranges are listed first and win, which is how Goa is
# separated from Maharashtra and Jharkhand from Bihar — both share a two-digit
# prefix with their neighbour and a two-digit table gets them wrong.
PIN_RANGES: list[tuple[int, int, str]] = [
    (110, 110, "Delhi"),
    (160, 160, "Chandigarh"),
    (403, 403, "Goa"),
    (605, 605, "Puducherry"),
    (737, 737, "Sikkim"),
    (744, 744, "Andaman and Nicobar Islands"),
    (246, 249, "Uttarakhand"),
    (262, 263, "Uttarakhand"),
    (813, 835, "Jharkhand"),
    (121, 136, "Haryana"),
    (140, 160, "Punjab"),
    (171, 177, "Himachal Pradesh"),
    (180, 194, "Jammu and Kashmir"),
    (201, 285, "Uttar Pradesh"),
    (301, 345, "Rajasthan"),
    (360, 396, "Gujarat"),
    (400, 445, "Maharashtra"),
    (450, 488, "Madhya Pradesh"),
    (490, 497, "Chhattisgarh"),
    (500, 509, "Telangana"),
    (515, 535, "Andhra Pradesh"),
    (560, 591, "Karnataka"),
    (600, 643, "Tamil Nadu"),
    (670, 695, "Kerala"),
    (700, 743, "West Bengal"),
    (751, 770, "Odisha"),
    (781, 788, "Assam"),
    (790, 792, "Arunachal Pradesh"),
    (793, 794, "Meghalaya"),
    (795, 795, "Manipur"),
    (796, 796, "Mizoram"),
    (797, 798, "Nagaland"),
    (799, 799, "Tripura"),
    (800, 855, "Bihar"),
]

# Where the private carriers thin out and India Post is the only answer. This
# is the whole reason the module exists, so it is data rather than a comment.
REMOTE_STATES = {
    "Jammu and Kashmir", "Arunachal Pradesh", "Meghalaya", "Manipur",
    "Mizoram", "Nagaland", "Tripura", "Sikkim",
    "Andaman and Nicobar Islands", "Himachal Pradesh",
}

METROS = {
    "110": "Delhi", "400": "Mumbai", "700": "Kolkata", "600": "Chennai",
    "560": "Bengaluru", "500": "Hyderabad", "380": "Ahmedabad", "411": "Pune",
}

ZONES = {
    "local":  ("Local", "स्थानीय"),
    "state":  ("Within the state", "राज्य के अंदर"),
    "metro":  ("Metro to metro", "महानगर से महानगर"),
    "india":  ("Rest of India", "बाकी भारत"),
    "remote": ("Remote / North-East", "दूरस्थ / पूर्वोत्तर"),
}


def _prefix(pincode: str) -> int | None:
    digits = "".join(ch for ch in (pincode or "") if ch.isdigit())
    if len(digits) != 6:
        return None
    return int(digits[:3])


def locate(pincode: str) -> dict:
    """Which state a pincode is in, and whether couriers bother going there."""
    p = _prefix(pincode)
    if p is None:
        return {"valid": False,
                "reason": "A pincode is six digits",
                "reason_hi": "पिनकोड छह अंकों का होता है"}
    for lo, hi, state in PIN_RANGES:
        if lo <= p <= hi:
            return {
                "valid": True, "pincode": pincode, "state": state,
                "metro": METROS.get(str(p), ""),
                "remote": state in REMOTE_STATES,
            }
    return {"valid": False,
            "reason": f"{pincode} is not a pincode we recognise",
            "reason_hi": f"{pincode} पहचाना नहीं गया"}


def zone_between(origin: str, destination: str) -> dict:
    """The rate zone between two pincodes, and why it is that zone."""
    a, b = locate(origin), locate(destination)
    if not a.get("valid"):
        return {"valid": False, **a}
    if not b.get("valid"):
        return {"valid": False, **b}

    if a["pincode"][:3] == b["pincode"][:3]:
        key = "local"
    elif b["remote"] or a["remote"]:
        key = "remote"
    elif a["state"] == b["state"]:
        key = "state"
    elif a["metro"] and b["metro"]:
        key = "metro"
    else:
        key = "india"

    label, label_hi = ZONES[key]
    return {"valid": True, "zone": key, "label": label, "label_hi": label_hi,
            "from": a, "to": b}


# -------------------------------------------------------------- rate cards
#
# base = first 500g, per_500g = each additional part-slab, days = promised
# transit. Published indicative slabs; GST is added on top, as the carriers do.
GST_RATE = 0.18

CARRIERS = [
    {
        "code": "indiapost-speed",
        "name": "India Post — Speed Post",
        "name_hi": "इंडिया पोस्ट — स्पीड पोस्ट",
        "everywhere": True,
        "rates": {
            "local":  {"base": 35, "per_500g": 15, "days": 2},
            "state":  {"base": 45, "per_500g": 20, "days": 3},
            "metro":  {"base": 60, "per_500g": 25, "days": 3},
            "india":  {"base": 70, "per_500g": 30, "days": 5},
            "remote": {"base": 90, "per_500g": 40, "days": 8},
        },
        "note": "Reaches every pincode in India. Slower to the North-East, "
                "but it goes.",
        "note_hi": "भारत के हर पिनकोड तक जाता है। पूर्वोत्तर में धीमा, पर "
                   "पहुँचता ज़रूर है।",
    },
    {
        "code": "indiapost-parcel",
        "name": "India Post — Registered Parcel",
        "name_hi": "इंडिया पोस्ट — रजिस्टर्ड पार्सल",
        "everywhere": True,
        "rates": {
            "local":  {"base": 25, "per_500g": 10, "days": 4},
            "state":  {"base": 32, "per_500g": 14, "days": 6},
            "metro":  {"base": 42, "per_500g": 18, "days": 7},
            "india":  {"base": 50, "per_500g": 22, "days": 9},
            "remote": {"base": 65, "per_500g": 30, "days": 14},
        },
        "note": "The cheapest tracked option. Worth it when the buyer is not "
                "in a hurry.",
        "note_hi": "सबसे सस्ता ट्रैक होने वाला विकल्प। जब जल्दी न हो तब सही है।",
    },
    {
        "code": "delhivery",
        "name": "Delhivery Surface",
        "name_hi": "डेल्हीवरी सरफेस",
        "everywhere": False,
        "rates": {
            "local":  {"base": 45, "per_500g": 18, "days": 2},
            "state":  {"base": 58, "per_500g": 24, "days": 3},
            "metro":  {"base": 68, "per_500g": 28, "days": 3},
            "india":  {"base": 82, "per_500g": 34, "days": 4},
            "remote": {"base": 0,  "per_500g": 0,  "days": 0},
        },
        "note": "Doorstep pickup where they operate. Not everywhere.",
        "note_hi": "जहाँ सेवा है वहाँ घर से पिकअप। हर जगह नहीं।",
    },
    {
        "code": "dtdc",
        "name": "DTDC Surface",
        "name_hi": "डीटीडीसी सरफेस",
        "everywhere": False,
        "rates": {
            "local":  {"base": 50, "per_500g": 20, "days": 2},
            "state":  {"base": 62, "per_500g": 26, "days": 3},
            "metro":  {"base": 74, "per_500g": 30, "days": 4},
            "india":  {"base": 88, "per_500g": 36, "days": 5},
            "remote": {"base": 0,  "per_500g": 0,  "days": 0},
        },
        "note": "Wide franchise network in small towns.",
        "note_hi": "छोटे शहरों में बड़ा फ्रैंचाइज़ी नेटवर्क।",
    },
]

# Packing a handicraft is not packing a book. A woven piece needs a liner, a
# blue-pottery bowl needs a box it cannot move inside. Charged openly rather
# than hidden in the freight rate.
PACKING = {
    "Textiles": (35, "Moisture-proof liner and a flat mailer"),
    "Pottery": (85, "Double-walled box with cushioning — this breaks"),
    "Metalwork": (60, "Rigid box, corner protection"),
    "Woodwork": (55, "Rigid box, corner protection"),
    "Jewellery": (40, "Small rigid box, tamper tape"),
    "Painting": (70, "Flat rigid sleeve, do-not-bend marking"),
    "Basketry": (45, "Oversized box so the weave is not crushed"),
}
DEFAULT_PACKING = (45, "Protective box and cushioning")


def _slabs(weight_g: int) -> int:
    """Additional 500g slabs beyond the first, rounded up as carriers do."""
    extra = max(0, int(weight_g) - 500)
    return (extra + 499) // 500


def quote(*, origin: str, destination: str, weight_g: int,
          category: str = "") -> dict:
    """Every carrier that will actually take this parcel, cheapest first."""
    z = zone_between(origin, destination)
    if not z.get("valid"):
        return {"serviceable": False, **z}

    zone = z["zone"]
    weight_g = max(100, int(weight_g or 500))
    slabs = _slabs(weight_g)
    pack_cost, pack_note = PACKING.get(category, DEFAULT_PACKING)

    options, refused = [], []
    for carrier in CARRIERS:
        card = carrier["rates"][zone]
        if not card["base"]:
            refused.append({
                "carrier": carrier["code"], "name": carrier["name"],
                "reason": f"Does not deliver to {z['to']['state']}",
                "reason_hi": f"{z['to']['state']} में सेवा नहीं देता",
            })
            continue
        freight = card["base"] + card["per_500g"] * slabs
        gst = round(freight * GST_RATE, 2)
        options.append({
            "carrier": carrier["code"],
            "name": carrier["name"], "name_hi": carrier["name_hi"],
            "freight": round(freight, 2),
            "gst": gst,
            "packing": pack_cost,
            "total": round(freight + gst + pack_cost, 2),
            "days": card["days"],
            "government": carrier["everywhere"],
            "note": carrier["note"], "note_hi": carrier["note_hi"],
        })

    options.sort(key=lambda o: o["total"])
    return {
        "serviceable": bool(options),
        "zone": zone, "zone_label": z["label"], "zone_label_hi": z["label_hi"],
        "from": z["from"], "to": z["to"],
        "weight_g": weight_g, "billed_slabs": slabs + 1,
        "packing_note": pack_note,
        "options": options,
        "unavailable": refused,
        "only_government": bool(options) and all(o["government"] for o in options),
        "disclaimer": (
            "Indicative published slabs plus 18% GST. Booking here records the "
            "despatch; handing it to the carrier's own system needs their API "
            "credentials."),
        "disclaimer_hi": (
            "सूचीबद्ध अनुमानित दरें और 18% GST। यहाँ बुकिंग खेप दर्ज करती है; "
            "कूरियर के अपने सिस्टम में भेजने के लिए उनकी API चाबी चाहिए।"),
    }


# ---------------------------------------------------------------- tracking
TRACK_STAGES = [
    ("booked", "Booked", "बुक हो गया"),
    ("picked_up", "Picked up", "उठा लिया गया"),
    ("in_transit", "In transit", "रास्ते में"),
    ("out_for_delivery", "Out for delivery", "डिलीवरी के लिए निकला"),
    ("delivered", "Delivered", "पहुँच गया"),
]
STAGE_LABELS = {k: (en, hi) for k, en, hi in TRACK_STAGES}


def new_awb(carrier: str) -> str:
    """An AWB shaped like the carrier's own, so it looks right on a receipt."""
    if carrier.startswith("indiapost"):
        # India Post articles are 13 characters: two letters, nine digits, IN.
        return ("E" + random.choice(string.ascii_uppercase)
                + f"{random.randrange(10 ** 8, 10 ** 9)}" + "IN")
    return f"{random.randrange(10 ** 11, 10 ** 12)}"


def pickup_window(now: datetime | None = None) -> datetime:
    """The next working-day pickup.

    Sunday is not a pickup day for any of these carriers, and an artisan told
    "collection tomorrow" on a Saturday who then waits in all Sunday stops
    believing the app.
    """
    now = now or datetime.now(timezone.utc)
    when = now + timedelta(days=1)
    if when.weekday() == 6:  # Sunday
        when += timedelta(days=1)
    return when.replace(hour=11, minute=0, second=0, microsecond=0)
