"""The PAVHAN assistant — a business manager, not a chatbot.

An artisan asking "mera basket kitne ka bikega?" does not want a paragraph
about pricing methodology; they want a number from their own catalogue. So
this module resolves a question to an INTENT, runs the real query behind it,
and answers from live data. The reply always carries the numbers it used, so
nothing here can quietly invent a price or an order count.

Questions it cannot map to an intent fall through to a grounded knowledge
base about the app itself — how to take a photo, what GI means, how the
commission works — which is what makes it useful for "random" questions too.

Matching is deliberately keyword-and-pattern based rather than a model call:
it must answer instantly, offline, in Hinglish, on a rural connection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Intents. Order matters — the first match wins, so put the specific ones
# above the general ones.
# ---------------------------------------------------------------------------
INTENTS: list[tuple[str, list[str]]] = [
    ("my_earnings", [
        r"earn|kamai|कमाई|income|profit|munafa|मुनाफ़ा|मुनाफा|revenue|आमदनी",
        r"paise?\b|पैसा|पैसे|kitna mila|कितना मिला|how much.*(made|make|get)",
    ]),
    ("my_orders", [
        r"\border|आर्डर|ऑर्डर|bikri|बिक्री|\bsale|sold|बिका|बिके|enquir|पूछताछ",
    ]),
    ("my_products", [
        r"my product|mere product|mera saman|mere saman|मेरे सामान|कितने सामान",
        r"kitne (product|saman|item)|kitna saman|\bmaal\b|माल|inventory|stock|listing",
        r"how many (product|item|thing)|products?\s+(do|have|hain)",
    ]),
    ("price_help", [
        r"price|pricing|daam|दाम|kimat|कीमत|keemat|\brate\b|भाव|bhav|मूल्य",
        r"kitne ka|kitna.*bech|कितने का|how much.*(sell|worth|charge)|charge",
    ]),
    ("find_buyers", [
        r"buyer|खरीदार|kharidar|customer|grahak|ग्राहक|bulk|थोक|b2b|export|निर्यात",
        r"who.*\bbuy\b|kaun khareed|कौन ख़रीद|कौन खरीद",
    ]),
    ("add_product", [
        r"add.*(product|item)|naya saman|नया सामान|list karna|कैसे डाल|कैसे जोड़",
        r"upload|डालना|how.*(list|add|sell) ",
    ]),
    ("photo_help", [
        r"photo|फोटो|image|picture|camera|कैमरा|tasveer|तस्वीर|background|बैकग्राउंड",
        r"studio|स्टूडियो|light|रोशनी|blur|धुंधल",
    ]),
    ("voice_help", [
        r"voice|आवाज़|आवाज|bolna|बोलना|\bmic\b|माइक|microphone|record|रिकॉर्ड|सुन",
        r"speak|बोलकर|hindi me bol",
    ]),
    ("gi_help", [
        r"\bgi\b|जीआई|geographical|\btag\b|प्रमाण|certificat|certified|असली",
    ]),
    ("commission_help", [
        r"commission|कमीशन|\bcut\b|\bfee\b|शुल्क|kitna leta|kitna lete|platform.*charge",
        r"आप कितना|tum kitna",
    ]),
    ("shipping_help", [
        r"ship|delivery|डिलीवरी|courier|कूरियर|भेज|bhej|\bpack|पैक|transport",
    ]),
    ("payment_help", [
        r"payment|भुगतान|\bbank\b|कब मिलेगा|when.*(paid|get money)|kab milega|पेमेंट",
        r"advance|एडवांस",
    ]),
    ("what_is_pavhan", [
        r"what is (this|the)? ?(app|pavhan)|pavhan kya|पवन क्या|पावहन क्या|about (this )?app",
        r"ye app kya|यह ऐप|यह क्या",
        r"who are you|tum kaun|आप कौन",
    ]),
    ("how_it_works", [
        r"how.*work|kaise kaam|कैसे काम|kya karta|process|तरीका|कैसे चलता|how.*use|kaise use",
    ]),
    ("language_help", [
        r"hindi|हिंदी|language|भाषा|english|bhasha|अंग्रेज़ी|translat",
    ]),
    ("greeting", [
        r"^\s*(hi|hello|namaste|नमस्ते|hey|salaam|प्रणाम|namaskar)\b",
    ]),
]


# ---------------------------------------------------------------------------
# Knowledge base. Every answer is something PAVHAN actually does — no
# aspirational claims, because an artisan will test them.
# ---------------------------------------------------------------------------
KNOWLEDGE: dict[str, dict[str, str]] = {
    "what_is_pavhan": {
        "en": "PAVHAN is your business manager. You photograph your craft and "
              "describe it out loud — I write the listing in Hindi and English, "
              "work out a fair price from your hours and materials, and find "
              "buyers who want exactly that kind of piece. You never have to "
              "type in English or edit a photo.",
        "hi": "पावहन आपका बिज़नेस मैनेजर है। आप सामान की फोटो लीजिए और बोलकर बता दीजिए — "
              "बाकी सब मैं करूँगा। विवरण हिंदी और अंग्रेज़ी दोनों में लिखूँगा, आपकी मेहनत "
              "और माल के हिसाब से सही दाम निकालूँगा, और ऐसे खरीदार ढूँढूँगा जिन्हें यही "
              "चीज़ चाहिए। न अंग्रेज़ी लिखनी है, न फोटो एडिट करनी है।",
    },
    "how_it_works": {
        "en": "Six steps, about two minutes. Photograph the piece, and the studio "
              "cleans up the background and lighting. Speak about it in your own "
              "language. Check the listing I wrote. Look at the price and the "
              "arithmetic behind it. Pick buyers from the matches. Publish.",
        "hi": "छह कदम, लगभग दो मिनट। फोटो लीजिए — स्टूडियो बैकग्राउंड और रोशनी ठीक कर "
              "देगा। अपनी भाषा में बोलिए। मैंने जो विवरण लिखा वह जाँच लीजिए। दाम और उसका "
              "पूरा हिसाब देखिए। खरीदार चुनिए। और डाल दीजिए।",
    },
    "photo_help": {
        "en": "Three rules and your photo will be good enough. Stand near a "
              "window in daylight. Put the piece on a plain white cloth. Hold the "
              "phone steady with the whole product in frame. The studio then "
              "removes the background, fixes the lighting and crops it to the "
              "square size marketplaces ask for.",
        "hi": "तीन बातें याद रखिए। एक — खिड़की के पास दिन की रोशनी में खड़े होइए। दो — सामान "
              "सादे सफ़ेद कपड़े पर रखिए। तीन — मोबाइल स्थिर रखिए और पूरा सामान फ्रेम में लाइए। "
              "इसके बाद स्टूडियो खुद बैकग्राउंड हटाकर, रोशनी ठीक करके, सही नाप में काट देगा।",
    },
    "voice_help": {
        "en": "Press the microphone and speak normally — Hindi, Hinglish or "
              "English all work. Say four things: what it is, what it is made of, "
              "how big it is, and how many days it took. If the mic does not "
              "start, the Speak screen shows exactly why and what to fix.",
        "hi": "माइक दबाकर सामान्य रूप से बोलिए — हिंदी, हिंग्लिश या अंग्रेज़ी, तीनों चलेंगी। "
              "चार बातें बताइए: यह क्या है, किस चीज़ से बना है, कितना बड़ा है, और कितने दिन "
              "लगे। माइक न चले तो उसी पन्ने पर कारण और उपाय लिखा मिलेगा।",
    },
    "gi_help": {
        "en": "A GI tag — Geographical Indication — is the government certifying "
              "that a craft genuinely belongs to its region, like Banarasi silk to "
              "Varanasi. Buyers pay more for it, so PAVHAN adds a 12% premium to "
              "the recommended price when your craft carries one.",
        "hi": "जीआई यानी भौगोलिक संकेत — सरकार का प्रमाण कि यह शिल्प वाकई उसी क्षेत्र का है, "
              "जैसे बनारसी रेशम वाराणसी का। खरीदार इसके लिए ज़्यादा देते हैं, इसलिए पावहन ऐसे "
              "शिल्प के दाम में 12% जोड़ता है।",
    },
    "commission_help": {
        "en": "PAVHAN keeps 5% of the sale price, and that is the only deduction. "
              "It is shown on every product page, so the buyer can see it too. A "
              "trader at your door typically keeps 55 to 60%.",
        "hi": "पावहन बिक्री का सिर्फ़ 5% रखता है, और इसके अलावा कोई कटौती नहीं है। यह हर सामान "
              "के पन्ने पर लिखा होता है, खरीदार को भी दिखता है। बिचौलिया आमतौर पर 55 से 60% "
              "रख लेता है।",
    },
    "shipping_help": {
        "en": "Each listing carries a lead time — the days you need to make and "
              "pack the piece — and buyers see it before they order, so nobody "
              "expects a shawl in two days. Pack craft-safe; that cost is already "
              "included in your recommended price.",
        "hi": "हर सामान पर तैयार होने का समय लिखा होता है — कितने दिन में आप बनाकर भेज "
              "सकते हैं। खरीदार ऑर्डर से पहले यह देख लेता है। पैकिंग का खर्च आपके सुझाए दाम "
              "में पहले से जुड़ा है।",
    },
    "payment_help": {
        "en": "For a retail order you receive 95% of the sale price. For a bulk "
              "order the terms are the buyer's — most pay part in advance and the "
              "rest on delivery, and each buyer's profile states their record of "
              "repeat orders so you can judge them.",
        "hi": "खुदरा बिक्री पर आपको दाम का 95% मिलता है। थोक ऑर्डर में शर्तें खरीदार की होती "
              "हैं — ज़्यादातर कुछ पैसा पहले और बाकी माल पहुँचने पर देते हैं। हर खरीदार के पन्ने "
              "पर उसका रिकॉर्ड लिखा होता है।",
    },
    "language_help": {
        "en": "Use the अ / A button at the top of any screen. It switches the "
              "whole app, including the price breakdown and the buyer-match "
              "reasons — not just the button labels. Your listing is written in "
              "both languages either way.",
        "hi": "किसी भी पन्ने पर ऊपर अ / A बटन दबाइए। पूरा ऐप बदल जाएगा — दाम का हिसाब और "
              "खरीदारों के कारण भी, सिर्फ़ बटन नहीं। आपका विवरण दोनों भाषाओं में बनता ही है।",
    },
    "add_product": {
        "en": "Press the big red button in the middle of the bottom bar. Photo "
              "first, then speak, and I take it from there.",
        "hi": "नीचे बीच वाला बड़ा लाल बटन दबाइए। पहले फोटो, फिर बोलिए — आगे का काम मेरा।",
    },
    "greeting": {
        "en": "Namaste. Ask me anything — your prices, your orders, how to "
              "photograph a piece, or what a GI tag means.",
        "hi": "नमस्ते! कुछ भी पूछिए — अपने दाम, अपने ऑर्डर, फोटो कैसे लें, या जीआई क्या होता है।",
    },
    "fallback": {
        "en": "I did not follow that. Try asking about your products, your "
              "orders, your earnings, pricing, buyers, or how to photograph a "
              "piece.",
        "hi": "यह मैं समझ नहीं पाया। अपने सामान, ऑर्डर, कमाई, दाम, खरीदार, या फोटो कैसे लें — "
              "इनमें से कुछ पूछिए।",
    },
}

SUGGESTIONS = {
    "hi": [
        "मेरे कितने सामान हैं?",
        "मेरी कमाई कितनी है?",
        "अच्छी फोटो कैसे लूँ?",
        "जीआई क्या होता है?",
        "पावहन कितना कमीशन लेता है?",
        "मेरे लिए खरीदार कौन हैं?",
    ],
    "en": [
        "How many products do I have?",
        "What have I earned so far?",
        "How do I take a good photo?",
        "What is a GI tag?",
        "How much commission does PAVHAN take?",
        "Which buyers match my work?",
    ],
}


@dataclass
class Answer:
    intent: str
    text: str
    data: dict = field(default_factory=dict)
    action: str | None = None          # a screen the app can jump to
    action_label: str = ""
    suggestions: list[str] = field(default_factory=list)
    confidence: int = 0


def detect_intent(message: str) -> tuple[str, int]:
    """Return (intent, confidence 0-100)."""
    text = (message or "").lower().strip()
    if not text:
        return "fallback", 0
    for intent, patterns in INTENTS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # A longer match against a longer question is stronger evidence.
                return intent, min(95, 62 + min(len(text), 60) // 3)
    return "fallback", 20
