"""WhatsApp, because that is the app that is already open.

An artisan will not check a dashboard every morning. They will check WhatsApp,
because their family, their cluster and their existing buyers are all already
there. Any notification this platform sends that does not arrive on WhatsApp
is a notification that arrives three days late.

The mechanism is deliberately the boring one: `wa.me` click-to-chat links. No
Business API, no template approval, no per-message cost, no onboarding — the
message opens pre-written in whichever WhatsApp the person already has, and
they press send. It works from the artisan's phone, the buyer's phone and a
laptop at a fair, on day one.

Messages are composed in the recipient's language and are written to be read
aloud, because they frequently will be. No links to anything that needs a
login, no jargon, and the amount always before the explanation — that is the
part that gets read.
"""

from __future__ import annotations

from urllib.parse import quote


def normalise_phone(phone: str, default_cc: str = "91") -> str:
    """An Indian mobile number in the shape `wa.me` wants: digits, with country
    code, and nothing else.

    Handles the four ways the same number gets typed in India: bare ten
    digits, a leading zero from a landline habit, `+91`, and `91` already
    present. A number that survives none of these is returned empty rather
    than guessed at — a WhatsApp link to the wrong person is worse than no
    link.
    """
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        return default_cc + digits
    if len(digits) == 11 and digits.startswith("0"):
        return default_cc + digits[1:]
    if len(digits) == 12 and digits.startswith(default_cc):
        return digits
    if len(digits) == 13 and digits.startswith("0" + default_cc):
        return digits[1:]
    # Already an international number of a plausible length.
    if 11 <= len(digits) <= 15:
        return digits
    return ""


def wa_link(phone: str, text: str) -> str:
    """Click-to-chat. Without a number it opens the contact picker instead,
    which is what you want for 'share this with anyone'."""
    body = quote(text, safe="")
    number = normalise_phone(phone)
    return f"https://wa.me/{number}?text={body}" if number else \
        f"https://wa.me/?text={body}"


def _money(amount: float) -> str:
    return f"{amount:,.0f}"


# ------------------------------------------------------------------ messages
def order_placed(*, artisan_name: str, buyer_name: str, quantity: int,
                 amount: float, payout: float, order_id: str,
                 lang: str = "hi") -> str:
    if lang == "hi":
        return (
            f"नमस्ते {artisan_name} जी 🙏\n\n"
            f"आपको नया ऑर्डर मिला है।\n\n"
            f"खरीदार: {buyer_name}\n"
            f"मात्रा: {quantity} पीस\n"
            f"कुल: ₹{_money(amount)}\n"
            f"आपको मिलेंगे: ₹{_money(payout)}\n"
            f"ऑर्डर नंबर: {order_id}\n\n"
            f"— PAVHAN")
    return (
        f"Hello {artisan_name} 🙏\n\n"
        f"You have a new order.\n\n"
        f"Buyer: {buyer_name}\n"
        f"Quantity: {quantity} pieces\n"
        f"Total: Rs.{_money(amount)}\n"
        f"You receive: Rs.{_money(payout)}\n"
        f"Order: {order_id}\n\n"
        f"— PAVHAN")


def payment_request(*, artisan_name: str, amount: float, upi_link_url: str,
                    product_title: str, lang: str = "en") -> str:
    """Sent by the artisan to the buyer. The UPI link is the whole message —
    everything else is there so the buyer knows what they are paying for."""
    if lang == "hi":
        return (
            f"नमस्ते 🙏\n\n"
            f"{product_title} के लिए ₹{_money(amount)} का भुगतान।\n\n"
            f"इस लिंक से सीधे UPI में भुगतान करें:\n{upi_link_url}\n\n"
            f"पैसा डिलीवरी तक सुरक्षित रखा जाता है।\n\n"
            f"— {artisan_name}, PAVHAN पर")
    return (
        f"Hello 🙏\n\n"
        f"Payment of Rs.{_money(amount)} for {product_title}.\n\n"
        f"Pay directly by UPI using this link:\n{upi_link_url}\n\n"
        f"The money is held safely until the piece is delivered.\n\n"
        f"— {artisan_name}, on PAVHAN")


def payment_received(*, amount: float, reference: str, lang: str = "hi") -> str:
    if lang == "hi":
        return (f"भुगतान मिल गया ✅\n\n₹{_money(amount)}\n"
                f"संदर्भ: {reference}\n\nडिलीवरी पर आपके UPI में भेज दिया जाएगा।\n\n— PAVHAN")
    return (f"Payment received ✅\n\nRs.{_money(amount)}\n"
            f"Reference: {reference}\n\nReleased to your UPI on delivery.\n\n— PAVHAN")


def shipment_booked(*, carrier: str, awb: str, days: int,
                    lang: str = "en") -> str:
    if lang == "hi":
        return (f"खेप बुक हो गई 📦\n\n{carrier}\n"
                f"ट्रैकिंग नंबर: {awb}\n"
                f"अनुमानित समय: {days} दिन\n\n— PAVHAN")
    return (f"Shipment booked 📦\n\n{carrier}\n"
            f"Tracking number: {awb}\n"
            f"Estimated: {days} days\n\n— PAVHAN")


def product_share(*, title: str, price: float, artisan_name: str,
                  region: str, url: str, lang: str = "en") -> str:
    """Shared by anyone, to anyone. This is how a craft actually travels."""
    if lang == "hi":
        return (f"*{title}*\n"
                f"₹{_money(price)}\n\n"
                f"{region} के {artisan_name} द्वारा हाथ से बनाया गया।\n\n"
                f"{url}\n\n"
                f"सीधे कारीगर से — बिना बिचौलिये के।")
    return (f"*{title}*\n"
            f"Rs.{_money(price)}\n\n"
            f"Handmade by {artisan_name} of {region}.\n\n"
            f"{url}\n\n"
            f"Bought directly from the artisan — no middleman.")


def stall_share(*, artisan_name: str, fair_name: str, url: str,
                lang: str = "en") -> str:
    if lang == "hi":
        return (f"{fair_name} में मेरा स्टॉल 🪡\n\n"
                f"मेला खत्म होने के बाद भी मेरा पूरा काम यहाँ देख सकते हैं:\n{url}\n\n"
                f"— {artisan_name}")
    return (f"My stall at {fair_name} 🪡\n\n"
            f"You can see all my work here, long after the fair closes:\n{url}\n\n"
            f"— {artisan_name}")


def pool_invite(*, lead_name: str, shg_name: str, quantity: int,
                allocated: int, payout: float, days: int,
                lang: str = "hi") -> str:
    """The message that turns six refusals into one accepted order."""
    if lang == "hi":
        return (
            f"नमस्ते 🙏\n\n"
            f"{shg_name} को {quantity} पीस का ऑर्डर मिल सकता है, "
            f"पर अकेले कोई नहीं बना सकता।\n\n"
            f"आपका हिस्सा: {allocated} पीस\n"
            f"आपको मिलेंगे: ₹{_money(payout)}\n"
            f"समय: {days} दिन\n\n"
            f"हिस्सा इस आधार पर है कि कौन कितना बना सकता है।\n\n"
            f"— {lead_name}, PAVHAN पर")
    return (
        f"Hello 🙏\n\n"
        f"{shg_name} can take an order for {quantity} pieces, but no one of us "
        f"can make that alone.\n\n"
        f"Your share: {allocated} pieces\n"
        f"You receive: Rs.{_money(payout)}\n"
        f"Time: {days} days\n\n"
        f"Shares are set by how much each of us can finish.\n\n"
        f"— {lead_name}, on PAVHAN")
