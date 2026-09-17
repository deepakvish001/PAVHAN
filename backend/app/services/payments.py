"""Money reaching the artisan, which is the promise this app opens with.

PAVHAN's welcome line tells the artisan, in Hindi, that it will not merely
take their product — it will pay them. Until an order could actually be paid
for, that was a slogan with a database behind it.

Two decisions shape this module.

**UPI, not a card gateway.** The buyer pays by UPI intent: a `upi://pay` link
that opens GPay, PhonePe or Paytm with the amount and the artisan's own VPA
already filled in. It needs no merchant onboarding, no settlement account and
no PCI surface, and — the part that matters — it is the payment rail rural
India already uses. An artisan can read a VPA off their own phone and check it
without going to a branch; they cannot do that with an IFSC and an account
number.

**Escrow, stated plainly.** The money is *held* between payment and delivery,
and both sides are told so in their own language. A buyer who pays a stranger
in a village wants to know the money is not gone if nothing arrives; an
artisan who ships first wants to know the money already exists. Holding it is
the only arrangement that answers both, and pretending otherwise would be the
dishonest choice.

What this module does **not** do is move real money. Confirmation is recorded
from the UTR the payer reads out of their own UPI app, and the app says so on
the screen. A real deployment replaces `confirm()` with a PSP webhook and
changes nothing else — the states, the split and the ledger are already the
ones a settlement provider reports.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote

# ---------------------------------------------------------------- the split
#
# 5% is what the order pipeline already applies (`artisan_payout = amount *
# 0.95`), and this module must not quietly disagree with it. Stated here once
# so the payment screen and the order screen cannot drift apart.
PLATFORM_FEE_RATE = 0.05

# What a trader at the door typically leaves behind. Same figure the pricing
# engine and the impact report use, for the same reason.
MIDDLEMAN_SHARE = 0.42

# A VPA is `something@handle`. NPCI allows a generous local part, so this
# checks shape rather than trying to be clever about what is inside it.
VPA_RE = re.compile(r"^[A-Za-z0-9.\-_]{2,256}@[A-Za-z][A-Za-z0-9.\-]{1,63}$")

# Recognised so the app can say "that looks like a PhonePe ID" back to the
# artisan as reassurance. An unknown handle is NOT rejected — new PSPs and
# bank handles appear constantly, and refusing one would lock out the exact
# person this app is for.
KNOWN_HANDLES = {
    "ybl": "PhonePe", "ibl": "PhonePe", "axl": "PhonePe",
    "okaxis": "Google Pay", "okhdfcbank": "Google Pay",
    "okicici": "Google Pay", "oksbi": "Google Pay",
    "paytm": "Paytm", "ptyes": "Paytm", "ptsbi": "Paytm",
    "apl": "Amazon Pay", "yapl": "Amazon Pay",
    "upi": "BHIM", "sbi": "SBI", "hdfcbank": "HDFC Bank",
    "icici": "ICICI Bank", "axisbank": "Axis Bank", "pnb": "Punjab National Bank",
    "barodampay": "Bank of Baroda", "cnrb": "Canara Bank", "uboi": "Union Bank",
    "jio": "Jio", "fbl": "Federal Bank", "idfcbank": "IDFC First",
    "kotak": "Kotak", "indus": "IndusInd", "airtel": "Airtel Payments Bank",
}

# The states an artisan actually asks about, in the words they ask in.
STATES = {
    "awaiting_payment": (
        "Waiting for the buyer to pay",
        "खरीदार के भुगतान का इंतज़ार",
        "The payment link has been sent. Nothing has moved yet."),
    "held": (
        "Paid — held safely until delivery",
        "भुगतान हो गया — डिलीवरी तक सुरक्षित रखा है",
        "The buyer has paid. The money is held and is released to you on delivery."),
    "released": (
        "Sent to your UPI",
        "आपके UPI में भेज दिया",
        "Released to the artisan's own UPI ID."),
    "refunded": (
        "Returned to the buyer",
        "खरीदार को वापस",
        "The order did not complete and the money went back."),
    "failed": (
        "Payment did not go through",
        "भुगतान नहीं हुआ",
        "The buyer's payment failed or was abandoned."),
}

# What may follow what. An order's money cannot go backwards any more than the
# order can.
TRANSITIONS = {
    "awaiting_payment": {"held", "failed"},
    "held": {"released", "refunded"},
    "released": set(),
    "refunded": set(),
    "failed": {"awaiting_payment"},
}

DISCLAIMER = {
    "en": ("PAVHAN does not hold a payment licence. Payments open in the "
           "buyer's own UPI app and settle directly to the artisan's VPA; "
           "confirmation here is recorded from the UTR the payer reads out of "
           "that app. A production deployment confirms it from the payment "
           "provider instead."),
    "hi": ("PAVHAN के पास भुगतान लाइसेंस नहीं है। भुगतान खरीदार के अपने UPI ऐप "
           "में खुलता है और सीधे कारीगर की VPA में जाता है; यहाँ पुष्टि उसी UTR "
           "से दर्ज होती है जो भुगतानकर्ता अपने ऐप में देखता है।"),
}


# --------------------------------------------------------------------- VPA
def check_vpa(vpa: str) -> dict:
    """Is this a UPI ID, and whose?

    Returns a verdict rather than raising, because this runs while the artisan
    is still typing and a half-entered VPA is not an error yet.
    """
    vpa = (vpa or "").strip()
    if not vpa:
        return {"valid": False, "reason": "Enter your UPI ID",
                "reason_hi": "अपनी UPI ID डालें"}
    if "@" not in vpa:
        return {"valid": False,
                "reason": "A UPI ID looks like name@bank — the @ is missing",
                "reason_hi": "UPI ID ऐसी होती है name@bank — @ नहीं है"}
    if not VPA_RE.match(vpa):
        return {"valid": False,
                "reason": "That does not look like a UPI ID. Check it in your "
                          "payment app under 'My UPI ID'.",
                "reason_hi": "यह UPI ID जैसी नहीं लग रही। अपने पेमेंट ऐप में "
                             "'My UPI ID' में देखें।"}

    handle = vpa.split("@", 1)[1].lower()
    provider = KNOWN_HANDLES.get(handle, "")
    return {
        "valid": True, "vpa": vpa, "handle": handle, "provider": provider,
        "reason": (f"Looks like a {provider} ID." if provider
                   else "Accepted. We could not recognise the bank handle, "
                        "so please check it once against your payment app."),
        "reason_hi": (f"{provider} की ID लग रही है।" if provider
                      else "स्वीकार कर लिया। बैंक हैंडल पहचान नहीं पाए, इसलिए "
                           "अपने पेमेंट ऐप से एक बार मिला लें।"),
    }


def upi_link(*, vpa: str, name: str, amount: float, note: str,
             reference: str) -> str:
    """A `upi://pay` intent link.

    On a real phone this opens the payment app with everything filled in, so
    the buyer confirms rather than types. Typing a VPA by hand is where
    money goes to the wrong person.

    Every value is percent-encoded: artisan names carry spaces and the note
    carries an ampersand-free but comma-bearing description, and an unencoded
    parameter silently truncates the amount on some apps.
    """
    params = [
        ("pa", vpa),
        ("pn", name or "PAVHAN artisan"),
        ("am", f"{amount:.2f}"),
        ("cu", "INR"),
        ("tn", note[:80]),
        ("tr", reference),
    ]
    query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params if v)
    return f"upi://pay?{query}"


# ------------------------------------------------------------------- split
def split(amount: float) -> dict:
    """Who gets what, with the comparison the artisan actually cares about."""
    amount = round(float(amount or 0), 2)
    fee = round(amount * PLATFORM_FEE_RATE, 2)
    artisan = round(amount - fee, 2)
    middleman = round(amount * MIDDLEMAN_SHARE, 2)
    return {
        "amount": amount,
        "platform_fee": fee,
        "platform_fee_rate": PLATFORM_FEE_RATE,
        "artisan_amount": artisan,
        "middleman_would_pay": middleman,
        "extra_vs_middleman": round(artisan - middleman, 2),
        "note": (f"You keep Rs.{artisan:,.0f} of Rs.{amount:,.0f}. A trader at "
                 f"your door would have paid about Rs.{middleman:,.0f}."),
        "note_hi": (f"₹{amount:,.0f} में से ₹{artisan:,.0f} आपके पास रहेंगे। "
                    f"दरवाज़े पर आने वाला व्यापारी लगभग ₹{middleman:,.0f} देता।"),
    }


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def describe(state: str) -> dict:
    label, label_hi, detail = STATES.get(
        state, (state, state, ""))
    return {"state": state, "label": label, "label_hi": label_hi,
            "detail": detail}


def reference_for(order_id: str) -> str:
    """A transaction reference the artisan can read aloud over a phone call.

    UPI allows up to 35 characters. Keeping it short and prefixed means a
    disputed payment can be found from the one thing both sides have: the
    reference on the receipt.
    """
    stamp = datetime.now(timezone.utc).strftime("%m%d%H%M")
    return f"PAVHAN{order_id[:8].upper()}{stamp}"
