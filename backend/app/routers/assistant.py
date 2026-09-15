"""The assistant endpoint: a question in, an answer grounded in live data out."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Buyer, Enquiry, Order, Product, User
from ..services.assistant import KNOWLEDGE, SUGGESTIONS, Answer, detect_intent
from ..services.matching import match_buyers

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _rupees(value: float) -> str:
    return f"₹{value:,.0f}"


def _artisan(db: Session, artisan_id: str | None) -> User | None:
    if artisan_id:
        found = db.get(User, artisan_id)
        if found:
            return found
    return db.scalars(select(User).where(User.role == "artisan")).first()


def _knowledge(intent: str, lang: str) -> str:
    block = KNOWLEDGE.get(intent) or KNOWLEDGE["fallback"]
    return block.get(lang, block["en"])


@router.get("/suggestions")
def suggestions(lang: str = "hi") -> dict:
    return {"lang": lang, "suggestions": SUGGESTIONS.get(lang, SUGGESTIONS["en"])}


@router.post("/ask")
def ask(
    message: str = Query(..., description="What the artisan asked, in any language"),
    lang: str = "hi",
    artisan_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Answer a free-form question.

    Data questions are resolved against this artisan's real catalogue rather
    than described in the abstract — "you have 4 products" beats "you can see
    your products on the Products screen".
    """
    intent, confidence = detect_intent(message)
    answer = Answer(intent=intent, text="", confidence=confidence)
    answer.suggestions = SUGGESTIONS.get(lang, SUGGESTIONS["en"])[:3]
    hi = lang == "hi"

    artisan = _artisan(db, artisan_id)
    products: list[Product] = []
    if artisan:
        products = list(db.scalars(
            select(Product).where(Product.artisan_id == artisan.id)).all())

    # ---- data-backed intents --------------------------------------------
    if intent == "my_products" and artisan:
        published = sum(1 for p in products if p.published)
        views = sum(p.views for p in products)
        if not products:
            answer.text = ("अभी आपने कोई सामान नहीं डाला है। नीचे बीच वाला बटन दबाकर "
                           "पहला सामान डालिए।" if hi else
                           "You have not listed anything yet. Press the button in the "
                           "middle of the bottom bar to add your first piece.")
        else:
            answer.text = (
                f"आपके पास {len(products)} सामान हैं, जिनमें से {published} बाज़ार में दिख "
                f"रहे हैं। अब तक इन्हें {views} बार देखा गया है।" if hi else
                f"You have {len(products)} products, {published} of them live. They have "
                f"been viewed {views} times so far.")
        answer.data = {"products": len(products), "published": published, "views": views}
        answer.action, answer.action_label = "/artisan/products", (
            "मेरा सामान देखिए" if hi else "See my products")

    elif intent == "my_orders" and artisan:
        ids = [p.id for p in products]
        orders = list(db.scalars(select(Order).where(Order.product_id.in_(ids)))) if ids else []
        enquiries = list(db.scalars(select(Enquiry).where(Enquiry.product_id.in_(ids)))) if ids else []
        open_enq = sum(1 for e in enquiries if e.status == "sent")
        answer.text = (
            f"आपके {len(orders)} ऑर्डर पूरे हुए हैं और {open_enq} पूछताछ खुली हैं।" if hi else
            f"You have {len(orders)} orders and {open_enq} open enquiries.")
        answer.data = {"orders": len(orders), "open_enquiries": open_enq}
        answer.action, answer.action_label = "/artisan/buyers", (
            "पूछताछ देखिए" if hi else "See enquiries")

    elif intent == "my_earnings" and artisan:
        ids = [p.id for p in products]
        orders = list(db.scalars(select(Order).where(Order.product_id.in_(ids)))) if ids else []
        earned = sum(o.artisan_payout for o in orders)
        gross = sum(o.amount for o in orders)
        middleman = gross * 0.42
        answer.text = (
            f"अब तक आपकी कमाई {_rupees(earned)} है। यही सामान बिचौलिये को देते तो लगभग "
            f"{_rupees(middleman)} मिलते — यानी {_rupees(earned - middleman)} ज़्यादा।"
            if hi else
            f"You have earned {_rupees(earned)} so far. Through a trader the same sales "
            f"would have paid you about {_rupees(middleman)} — you are "
            f"{_rupees(earned - middleman)} ahead.")
        answer.data = {"earnings": round(earned, 2), "gross": round(gross, 2),
                       "extra_vs_middleman": round(earned - middleman, 2)}
        answer.action, answer.action_label = "/artisan", ("घर पन्ना" if hi else "Open dashboard")

    elif intent == "price_help":
        if products:
            dearest = max(products, key=lambda p: p.price)
            answer.text = (
                f"दाम आपकी मेहनत के घंटों, माल के खर्च, डिज़ाइन की बारीकी और मौसम की माँग "
                f"से निकलता है। जैसे आपका «{dearest.title}» {_rupees(dearest.price)} पर है, "
                f"जिसमें से {_rupees(dearest.price * 0.95)} आपको मिलते हैं। नया सामान डालते "
                f"समय पूरा हिसाब दिखता है।" if hi else
                f"The price is built from your hours, your material cost, the intricacy "
                f"the camera measured and the season's demand. Your «{dearest.title}» sits "
                f"at {_rupees(dearest.price)}, of which {_rupees(dearest.price * 0.95)} "
                f"reaches you. The full arithmetic is shown when you list a piece.")
            answer.data = {"example_product": dearest.title, "price": dearest.price}
        else:
            answer.text = (
                "दाम आपकी मेहनत के घंटे, माल का खर्च और बाज़ार की माँग जोड़कर निकाला जाता है — "
                "और पूरा हिसाब आपको दिखाया जाता है, ताकि आप किसी को भी दिखा सकें।" if hi else
                "The price is your hours plus your material cost plus what the market will "
                "bear — and the whole calculation is shown to you, so you can show it to "
                "anyone who argues.")
        answer.action, answer.action_label = "/add", ("दाम निकालिए" if hi else "Price a piece")

    elif intent == "find_buyers":
        buyers = list(db.scalars(select(Buyer).where(Buyer.active.is_(True))).all())
        if products and buyers:
            best_product = max(products, key=lambda p: p.quality_score)
            matches = match_buyers(best_product, buyers, limit=3)
            names = ", ".join(m.name for m in matches)
            answer.text = (
                f"{len(buyers)} खरीदार जुड़े हैं। आपके «{best_product.title}» के लिए सबसे "
                f"अच्छे मेल हैं: {names}। हर एक के आगे लिखा है कि वह क्यों मेल खाता है।"
                if hi else
                f"{len(buyers)} buyers are on the platform. For your «{best_product.title}» "
                f"the strongest matches are {names}. Each one shows why it matched.")
            answer.data = {"buyers": len(buyers),
                           "top": [{"name": m.name, "score": m.score} for m in matches]}
        else:
            answer.text = (f"{len(buyers)} खरीदार जुड़े हैं। सामान डालते ही मैं बता दूँगा कि "
                           f"कौन आपके काम से मेल खाता है।" if hi else
                           f"{len(buyers)} buyers are on the platform. List a piece and I "
                           f"will tell you which of them fit it.")
        answer.action, answer.action_label = "/artisan/buyers", (
            "खरीदार देखिए" if hi else "See buyers")

    else:
        answer.text = _knowledge(intent, lang)
        if intent in ("photo_help", "voice_help", "add_product", "how_it_works"):
            answer.action, answer.action_label = "/add", (
                "अभी शुरू कीजिए" if hi else "Start now")

    return {
        "intent": answer.intent,
        "confidence": answer.confidence,
        "text": answer.text,
        "data": answer.data,
        "action": answer.action,
        "action_label": answer.action_label,
        "suggestions": answer.suggestions,
        "lang": lang,
    }
