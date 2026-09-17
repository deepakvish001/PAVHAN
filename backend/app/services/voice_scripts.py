"""The PAVHAN voice guide.

An artisan who has never listed a product online does not need a tooltip, they
need someone talking them through it. Every screen therefore has a spoken
script, in Hindi and English, written the way a helpful person would actually
say it out loud — short sentences, no jargon, one instruction at a time.

Scripts are served from the API rather than hardcoded in the app so they can be
corrected, translated and A/B tested without shipping a new build.
"""

from __future__ import annotations

# Spoken text avoids symbols the browser speech engine reads awkwardly:
# no "₹" (it says "rupee sign"), no "&", no bare numerals above 9999.

WELCOME = {
    "artisan": {
        "hi": (
            "स्वागत है आपका पावहन में। यहाँ हम आपसे सिर्फ़ सामान नहीं लेंगे, "
            "आपको उसका पूरा दाम भी दिलाएँगे। आप बस बोलिए — फोटो खींचिए और बोलकर बताइए "
            "कि आपने क्या बनाया है। बाकी सब मैं कर दूँगा।"
        ),
        "en": (
            "Welcome to PAVHAN. Here we do not just take your craft from you — we make "
            "sure you are paid properly for it. Just take a photo and speak. I will "
            "write the listing, set a fair price and find you buyers."
        ),
    },
    "customer": {
        "hi": (
            "पावहन में आपका स्वागत है। यहाँ हर चीज़ हाथ से बनी है और सीधे कारीगर से आती है। "
            "आप अपना बजट बताइए, मैं आपके लिए सही चीज़ ढूँढ दूँगा।"
        ),
        "en": (
            "Welcome to PAVHAN. Everything here is handmade and comes straight from the "
            "artisan who made it. Tell me your budget and what you are looking for, and "
            "I will find it for you."
        ),
    },
    "b2b": {
        "hi": (
            "पावहन में आपका स्वागत है। यहाँ आपको सत्यापित कारीगर, थोक कीमत और "
            "जीआई प्रमाणित शिल्प मिलेंगे। बताइए आपको किस श्रेणी में कितनी मात्रा चाहिए।"
        ),
        "en": (
            "Welcome to PAVHAN. You get verified artisan clusters, transparent bulk "
            "pricing and GI-tagged craft with documented provenance. Tell me the "
            "category and the quantity you need."
        ),
    },
    "exporter": {
        "hi": (
            "पावहन में आपका स्वागत है। निर्यात के लिए जीआई प्रमाणित शिल्प, "
            "क्लस्टर क्षमता और तैयार दस्तावेज़ — सब यहीं मिलेगा।"
        ),
        "en": (
            "Welcome to PAVHAN. GI-tagged craft, verified cluster capacity and "
            "export-ready documentation, all in one place."
        ),
    },
}

# screen key -> {lang: text}. `{...}` placeholders are filled by the API layer.
SCREENS: dict[str, dict[str, str]] = {
    "role_select": {
        "hi": "पहले यह बताइए कि आप यहाँ किस काम से आए हैं। कारीगर हैं, खरीदार हैं, "
              "या थोक में सामान लेना चाहते हैं? बस उस डिब्बे पर दबाइए।",
        "en": "First, tell me why you are here. Are you an artisan, a shopper, or a "
              "business buying in bulk? Just tap the card that fits you.",
    },
    "artisan_home": {
        "hi": "यह आपका घर पन्ना है। नया सामान डालने के लिए बीच वाले बड़े बटन पर दबाइए। "
              "आपकी अब तक की कमाई और आपके सामान नीचे दिख रहे हैं।",
        "en": "This is your home screen. To add something new, press the big button in "
              "the middle. Your earnings so far and your listed products are below.",
    },
    "capture_photo": {
        "hi": "अब अपने सामान की फोटो लीजिए। तीन बातें याद रखिए। एक — दिन की रोशनी में, "
              "खिड़की के पास खड़े होइए। दो — सामान को सादे सफ़ेद कपड़े पर रखिए। "
              "तीन — मोबाइल को हिलने मत दीजिए, और पूरा सामान फ्रेम में आना चाहिए। "
              "तैयार हैं? तो कैमरा बटन दबाइए।",
        "en": "Now take a photo of your piece. Three things. One — stand near a window "
              "in daylight. Two — place it on a plain white cloth. Three — hold the "
              "phone steady and keep the whole piece inside the frame. Ready? Press the "
              "camera button.",
    },
    "photo_feedback": {
        "hi": "फोटो देख ली मैंने। {tip}",
        "en": "I have looked at your photo. {tip}",
    },
    "voice_record": {
        "hi": "अब माइक का बटन दबाकर बोलिए। अपनी ही भाषा में बोलिए, कोई जल्दी नहीं है। "
              "चार बातें ज़रूर बताइए — यह क्या चीज़ है, किस चीज़ से बनी है, "
              "कितनी बड़ी है, और इसे बनाने में कितने दिन लगे। "
              "बोलकर हो जाए तो वही बटन दोबारा दबा दीजिए।",
        "en": "Now press the microphone and speak. Use your own language, there is no "
              "hurry. Tell me four things — what it is, what it is made of, how big it "
              "is, and how many days it took you to make. Press the same button again "
              "when you are done.",
    },
    "voice_listening": {
        "hi": "मैं सुन रहा हूँ। बोलते रहिए।",
        "en": "I am listening. Keep speaking.",
    },
    "voice_missing": {
        "hi": "आपने {missing} के बारे में नहीं बताया। यह बताना ज़रूरी है, इसी से आपका दाम तय होगा। "
              "माइक दबाकर बस इतना और बोल दीजिए।",
        "en": "You did not mention {missing}. This matters — it is what sets your price. "
              "Press the mic and just add that.",
    },
    "listing_review": {
        "hi": "देखिए, आपकी बात से मैंने यह विवरण बनाया है। आपने जो बोला वही लिखा है, "
              "कुछ भी अपनी तरफ़ से नहीं जोड़ा। अगर कुछ ग़लत लगे तो उस डिब्बे पर दबाकर "
              "सुधार दीजिए। ठीक लगे तो नीचे आगे बढ़िए।",
        "en": "Here is the listing I wrote from what you told me. I only used what you "
              "actually said — nothing is invented. If anything is wrong, tap that box "
              "and correct it. If it looks right, continue below.",
    },
    "pricing": {
        "hi": "अब सबसे ज़रूरी बात — दाम। मैंने आपकी मेहनत के {hours} घंटे, कच्चे माल का ख़र्च, "
              "और बाज़ार का भाव जोड़कर यह कीमत निकाली है। बिचौलिया आपको इससे बहुत कम देता है। "
              "पूरा हिसाब नीचे लिखा है — कोई भी दाम पूछे तो आप यही दिखा दीजिएगा।",
        "en": "Now the most important part — the price. I added up your hours of work, "
              "your material cost and the current market rate. A middleman would pay you "
              "far less than this. The full calculation is shown below — show it to "
              "anyone who questions your price.",
    },
    "buyer_match": {
        "hi": "ये रहे वो खरीदार जिन्हें बिल्कुल यही चीज़ चाहिए। हर एक के आगे लिखा है कि "
              "वह आपसे क्यों मेल खाता है और कितने पीस ले सकता है। जो ठीक लगे उसे "
              "संदेश भेज दीजिए — संदेश मैंने आपके लिए पहले से लिख रखा है।",
        "en": "These are the buyers who want exactly this kind of piece. Each one shows "
              "why it matches you and how many pieces they usually order. Send a message "
              "to whichever you like — I have already written it for you.",
    },
    "published": {
        "hi": "बधाई हो! आपका सामान अब पूरे भारत के खरीदारों को दिख रहा है। "
              "कोई पूछताछ आएगी तो मैं आपको बता दूँगा। अब अगला सामान डालिए?",
        "en": "Well done! Your piece is now visible to buyers across India. I will tell "
              "you as soon as an enquiry comes in. Shall we add the next one?",
    },
    "marketplace": {
        "hi": "यहाँ हर चीज़ सीधे कारीगर से आती है। ऊपर खोज में जो चाहिए वह लिख दीजिए, "
              "या बोलकर बता दीजिए। दाम के हिसाब से छाँटना हो तो छन्नी वाले बटन पर दबाइए।",
        "en": "Everything here comes straight from the artisan. Type what you want in the "
              "search bar above, or just say it out loud. Use the filter button to narrow "
              "it down by price.",
    },
    "product_detail": {
        "hi": "यह चीज़ {region} में हाथ से बनाई गई है। नीचे लिखा है कि इसे किसने बनाया "
              "और उसे इसमें से कितना मिलेगा।",
        "en": "This piece was made by hand in {region}. Below you can see who made it and "
              "exactly how much of your payment reaches them.",
    },
    "b2b_home": {
        "hi": "यहाँ आप श्रेणी, मात्रा और बजट के हिसाब से सत्यापित कारीगर ढूँढ सकते हैं।",
        "en": "Here you can find verified artisans by category, order quantity and budget.",
    },
    "search": {
        "hi": "खोजने के लिए बोलिए या लिखिए। हिंदी और अंग्रेज़ी, दोनों चलेगी।",
        "en": "Speak or type to search. Hindi and English both work.",
    },
    "mic_denied": {
        "hi": "माइक की अनुमति नहीं मिली। ऊपर पते वाली पट्टी में ताले के निशान पर दबाकर "
              "माइक चालू कर दीजिए, या नीचे लिखकर बता दीजिए।",
        "en": "I could not get microphone permission. Tap the lock icon in the address "
              "bar and allow the microphone, or just type your description below.",
    },
    "mic_unsupported": {
        "hi": "इस ब्राउज़र में बोलकर लिखने की सुविधा नहीं है। क्रोम में खोलिए, "
              "या नीचे लिखकर बता दीजिए — दोनों से काम हो जाएगा।",
        "en": "This browser cannot do speech to text. Open PAVHAN in Chrome, or simply "
              "type your description below — both work.",
    },
    "outbox": {
        "hi": "{line} सिग्नल न हो तब भी आप सामान रिकॉर्ड करते रहिए। जैसे ही नेटवर्क "
              "आएगा, ये अपने आप चले जाएँगे — आपको कुछ नहीं करना पड़ेगा।",
        "en": "{line} Keep recording even when there is no signal. The moment the "
              "network returns these go on their own — you do not have to do anything.",
    },
    "earnings": {
        "hi": "यहाँ आपका पैसा दिखता है। जो आ चुका है, जो डिलीवरी तक रोका हुआ है, और "
              "जो अभी आना बाकी है। पैसा सीधे आपकी अपनी यूपीआई आईडी में जाता है — "
              "बीच में कोई नहीं।",
        "en": "This is your money. What has arrived, what is being held until delivery, "
              "and what is still to come. It goes straight to your own UPI ID — nobody "
              "stands in between.",
    },
    "shipping": {
        "hi": "अब इसे भेजना है। मैंने उन्हीं कूरियर के दाम दिखाए हैं जो सचमुच आपके "
              "पिनकोड तक आते हैं। जहाँ निजी कूरियर नहीं जाते, वहाँ इंडिया पोस्ट जाता है।",
        "en": "Now to send it. I have priced only the carriers that actually come to "
              "your pincode. Where the private couriers do not go, India Post does.",
    },
    "pooling": {
        "hi": "यह ऑर्डर अकेले पूरा करना मुश्किल है, इसलिए इसे अपने समूह में बाँट "
              "लीजिए। हिस्सा इस आधार पर बँटता है कि समय-सीमा तक कौन कितना बना सकता है, "
              "और हर किसी को उसी हिसाब से पैसा मिलता है।",
        "en": "This order is hard to fill alone, so share it across your group. The "
              "split is based on how much each of you can finish before the deadline, "
              "and everyone is paid for exactly that.",
    },
}

TIPS = {
    "artisan": {
        "hi": [
            "एक ही चीज़ की तीन फोटो डालिए — पूरी, पास से, और किसी के हाथ में। बिक्री दोगुनी हो जाती है।",
            "बनाने में कितने दिन लगे यह ज़रूर बताइए। दाम इसी से तय होता है।",
            "त्योहार से एक महीना पहले सामान डालिए, तब दाम सबसे अच्छा मिलता है।",
            "अपनी कहानी बताइए — यह काम आपने किससे सीखा। खरीदार कहानी के लिए ज़्यादा देते हैं।",
        ],
        "en": [
            "Add three photos of the same piece — full, close-up, and held in a hand. It doubles enquiries.",
            "Always say how many days it took. That is what sets your price.",
            "List a month before a festival — that is when prices are strongest.",
            "Tell your story — who taught you this craft. Buyers pay more for a story they can retell.",
        ],
    },
    "customer": {
        "hi": [
            "हर चीज़ पर लिखा है कि कारीगर को कितना मिलेगा।",
            "जीआई का निशान मतलब सरकार से प्रमाणित असली शिल्प।",
        ],
        "en": [
            "Every listing shows exactly how much reaches the artisan.",
            "The GI badge means the craft is government-certified as genuine to its region.",
        ],
    },
    "b2b": {
        "hi": [
            "थोक में 50 पीस से ऊपर दाम अपने आप कम हो जाता है।",
            "क्लस्टर क्षमता देखकर ही ऑर्डर दीजिए ताकि समय पर मिल जाए।",
        ],
        "en": [
            "Bulk pricing steps down automatically above 50 pieces.",
            "Check cluster capacity before ordering so your lead time is realistic.",
        ],
    },
}

ROLES = [
    {
        "key": "artisan",
        "title": "I make craft",
        "title_hi": "मैं कारीगर हूँ",
        "subtitle": "List by voice, get a fair price, reach buyers",
        "subtitle_hi": "बोलकर सामान डालिए, सही दाम पाइए",
        "icon": "🧵",
        "accent": "#B03A2E",
    },
    {
        "key": "customer",
        "title": "I want to buy",
        "title_hi": "मुझे ख़रीदना है",
        "subtitle": "Handmade pieces, straight from the maker",
        "subtitle_hi": "सीधे कारीगर से हस्तनिर्मित सामान",
        "icon": "🛍️",
        "accent": "#1F6F5C",
    },
    {
        "key": "b2b",
        "title": "I buy in bulk",
        "title_hi": "मैं थोक में लेता हूँ",
        "subtitle": "Verified clusters, bulk pricing, real capacity",
        "subtitle_hi": "सत्यापित कारीगर, थोक भाव",
        "icon": "🏬",
        "accent": "#1B4F72",
    },
    {
        "key": "exporter",
        "title": "I export craft",
        "title_hi": "मैं निर्यात करता हूँ",
        "subtitle": "GI-tagged sourcing with documented provenance",
        "subtitle_hi": "जीआई प्रमाणित शिल्प, पूरे दस्तावेज़",
        "icon": "🌍",
        "accent": "#7D6608",
    },
]


def welcome(role: str, lang: str = "hi") -> str:
    block = WELCOME.get(role, WELCOME["customer"])
    return block.get(lang, block["en"])


def screen_script(screen: str, lang: str = "hi", **fields) -> str:
    block = SCREENS.get(screen)
    if not block:
        return ""
    text = block.get(lang, block.get("en", ""))
    if fields:
        try:
            text = text.format(**fields)
        except (KeyError, IndexError):
            pass
    return text


def tips(role: str, lang: str = "hi") -> list[str]:
    block = TIPS.get(role, TIPS["customer"])
    return block.get(lang, block["en"])
