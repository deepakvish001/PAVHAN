"""Understanding what the artisan actually said.

Artisans speak Hinglish: "Yeh Banarasi handwoven silk saree hai, 5.5 metre ka
hai, 450 gram, do din lage." Devanagari, Roman Hindi and English turn up in the
same sentence, so every extractor here accepts all three.

This module never invents facts. If the artisan did not mention weight, weight
comes back as None and the listing generator leaves that field for the artisan
to fill — an empty field is honest, a hallucinated one is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import vocab_regional as regional
from .languages import detect as detect_script_language
from .taxonomy import CRAFTS, Craft

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------
COLOUR_WORDS: dict[str, str] = {
    "red": "Red", "laal": "Red", "lal": "Red", "लाल": "Red",
    "maroon": "Maroon", "मैरून": "Maroon",
    "blue": "Blue", "neela": "Blue", "nila": "Blue", "नीला": "Blue",
    "navy": "Navy", "indigo": "Indigo", "neel": "Indigo", "नील": "Indigo",
    "green": "Green", "hara": "Green", "hari": "Green", "हरा": "Green",
    "yellow": "Yellow", "peela": "Yellow", "pila": "Yellow", "पीला": "Yellow",
    "golden": "Gold", "gold": "Gold", "sunehra": "Gold", "सुनहरा": "Gold", "सोनेरी": "Gold",
    "silver": "Silver", "chandi": "Silver", "चांदी": "Silver",
    "black": "Black", "kala": "Black", "kaala": "Black", "काला": "Black",
    "white": "White", "safed": "White", "सफ़ेद": "White", "सफेद": "White",
    "pink": "Pink", "gulabi": "Pink", "गुलाबी": "Pink",
    "orange": "Orange", "narangi": "Orange", "नारंगी": "Orange",
    "purple": "Purple", "baingani": "Purple", "बैंगनी": "Purple",
    "brown": "Brown", "bhura": "Brown", "भूरा": "Brown",
    "cream": "Cream", "क्रीम": "Cream",
    "beige": "Beige", "grey": "Grey", "gray": "Grey", "स्लेटी": "Grey",
    "turquoise": "Turquoise", "firozi": "Turquoise", "फ़िरोज़ी": "Turquoise",
    "magenta": "Magenta", "rani": "Magenta", "रानी": "Magenta",
    "mustard": "Mustard", "sarson": "Mustard", "सरसों": "Mustard",
    "teal": "Teal", "rust": "Rust", "copper": "Copper", "tambe": "Copper",
    "terracotta": "Terracotta", "olive": "Olive", "maroon rang": "Maroon",
}

MATERIAL_WORDS: dict[str, str] = {
    "silk": "Pure Silk", "resham": "Pure Silk", "रेशम": "Pure Silk", "सिल्क": "Pure Silk",
    "cotton": "Cotton", "sooti": "Cotton", "suti": "Cotton", "सूती": "Cotton", "कपास": "Cotton",
    "mulmul": "Mulmul", "muslin": "Mulmul", "मलमल": "Mulmul",
    "khadi": "Khadi", "खादी": "Khadi",
    "wool": "Wool", "oon": "Wool", "ऊन": "Wool", "woolen": "Wool",
    "pashmina": "Pashmina Wool", "पश्मीना": "Pashmina Wool",
    "clay": "Terracotta Clay", "mitti": "Terracotta Clay", "मिट्टी": "Terracotta Clay",
    "terracotta": "Terracotta Clay",
    "ceramic": "Quartz Ceramic", "sirামik": "Quartz Ceramic",
    "brass": "Brass", "pital": "Brass", "पीतल": "Brass",
    "bronze": "Bell Metal", "kansa": "Bell Metal", "कांसा": "Bell Metal",
    "copper": "Copper", "tamba": "Copper", "तांबा": "Copper",
    "wood": "Wood", "lakdi": "Wood", "lakadi": "Wood", "लकड़ी": "Wood",
    "bamboo": "Bamboo", "bans": "Bamboo", "baans": "Bamboo", "बाँस": "Bamboo", "बांस": "Bamboo",
    "cane": "Cane", "bent": "Cane", "बेंत": "Cane",
    "jute": "Jute", "पटसन": "Jute", "जूट": "Jute",
    "paper": "Handmade Paper", "kagaz": "Handmade Paper", "कागज़": "Handmade Paper",
    "leather": "Leather", "chamda": "Leather", "चमड़ा": "Leather",
    "stone": "Stone", "pathar": "Stone", "पत्थर": "Stone",
    "silver": "Silver", "chandi": "Silver", "चांदी": "Silver",
    "cloth": "Cotton", "kapda": "Cotton", "fabric": "Cotton", "कपड़ा": "Cotton",
    "canvas": "Canvas", "कैनवास": "Canvas",
    "zari": "Zari", "ज़री": "Zari", "linen": "Linen", "velvet": "Velvet",
    "glass": "Glass", "kaanch": "Glass", "कांच": "Glass",
    "shell": "Sea Shell", "coconut": "Coconut Shell", "grass": "Sabai Grass",
    "sabai": "Sabai Grass", "iron": "Wrought Iron", "loha": "Wrought Iron", "लोहा": "Wrought Iron",
}

TECHNIQUE_WORDS: dict[str, str] = {
    "handwoven": "Handwoven", "hand woven": "Handwoven", "bunai": "Handwoven",
    "बुनाई": "Handwoven", "handloom": "Handloom", "हथकरघा": "Handloom",
    "hand painted": "Hand-painted", "handpainted": "Hand-painted",
    "chitrakari": "Hand-painted", "चित्रकारी": "Hand-painted",
    "embroidery": "Hand Embroidery", "kadhai": "Hand Embroidery", "कढ़ाई": "Hand Embroidery",
    "carved": "Hand-carved", "nakkashi": "Hand-carved", "नक्काशी": "Hand-carved",
    "block print": "Block Printed", "chhapai": "Block Printed", "छपाई": "Block Printed",
    "moulded": "Hand-moulded", "chaak": "Wheel-thrown", "चाक": "Wheel-thrown",
    "cast": "Lost-wax Cast", "dhalai": "Lost-wax Cast", "ढलाई": "Lost-wax Cast",
    "zari": "Zari Work", "ज़री": "Zari Work", "जरी": "Zari Work",
    "inlay": "Inlay Work", "jadai": "Inlay Work", "जड़ाई": "Inlay Work",
    "hand made": "Handmade", "handmade": "Handmade", "haath se": "Handmade",
    "हाथ से": "Handmade", "hath se": "Handmade",
}

REGION_WORDS: dict[str, str] = {
    "banaras": "Varanasi", "banarasi": "Varanasi", "varanasi": "Varanasi",
    "बनारस": "Varanasi", "वाराणसी": "Varanasi",
    "jaipur": "Jaipur", "जयपुर": "Jaipur",
    "lucknow": "Lucknow", "लखनऊ": "Lucknow",
    "kashmir": "Srinagar", "srinagar": "Srinagar", "कश्मीर": "Srinagar",
    "bhagalpur": "Bhagalpur", "madhubani": "Madhubani", "मधुबनी": "Madhubani",
    "mithila": "Madhubani", "bastar": "Bastar", "बस्तर": "Bastar",
    "bidar": "Bidar", "channapatna": "Channapatna", "kutch": "Kutch", "कच्छ": "Kutch",
    "puri": "Puri", "odisha": "Odisha", "bengal": "West Bengal", "बंगाल": "West Bengal",
    "assam": "Assam", "असम": "Assam", "punjab": "Punjab", "पंजाब": "Punjab",
    "kolkata": "Kolkata", "nathdwara": "Nathdwara", "moradabad": "Moradabad",
    "jodhpur": "Jodhpur", "udaipur": "Udaipur", "agra": "Agra", "delhi": "Delhi",
    "gujarat": "Gujarat", "rajasthan": "Rajasthan", "राजस्थान": "Rajasthan",
}

# Regional languages fold straight into the existing tables: the canonical
# values are identical, so nothing downstream has to know which language the
# artisan spoke. Indic scripts never collide, so a single flat lookup is safe.
COLOUR_WORDS.update(regional.all_values(regional.COLOURS))
MATERIAL_WORDS.update(regional.all_values(regional.MATERIALS))
TECHNIQUE_WORDS.update(regional.all_values(regional.TECHNIQUES))

CARE_PATTERNS: list[tuple[str, str]] = [
    (r"dry\s*clean", "Dry clean only"),
    (r"ड्राई\s*क्लीन", "Dry clean only"),
    (r"hand\s*wash|haath\s*se\s*dho|हाथ\s*से\s*धो", "Hand wash only"),
    (r"machine\s*wash", "Machine wash gentle"),
    (r"thande\s*pani|cold\s*water|ठंडे\s*पानी", "Wash in cold water"),
    (r"dhoop\s*se\s*bacha|avoid\s*sun|धूप\s*से\s*बचा", "Keep away from direct sunlight"),
    (r"sookhi\s*jagah|dry\s*place|सूखी\s*जगह", "Store in a dry place"),
]

UNIT_MAP = {
    "metre": "metre", "meter": "metre", "mtr": "metre", "m": "metre", "मीटर": "metre",
    "gram": "gram", "gm": "gram", "g": "gram", "ग्राम": "gram",
    "kg": "kg", "kilo": "kg", "kilogram": "kg", "किलो": "kg",
    "inch": "inch", "inches": "inch", "इंच": "inch",
    "cm": "cm", "feet": "feet", "foot": "feet", "ft": "feet", "फुट": "feet",
}

HINDI_NUMBERS: dict[str, float] = {
    # English words
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "ninety": 90, "hundred": 100, "half": 0.5,
    # Roman Hindi -- how an artisan actually types or is transcribed
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "chah": 6, "chhah": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "dus": 10, "gyarah": 11, "barah": 12, "baarah": 12, "terah": 13, "chaudah": 14,
    "pandrah": 15, "pandhrah": 15, "solah": 16, "satrah": 17, "atharah": 18,
    "unnees": 19, "bees": 20, "pachees": 25, "tees": 30, "chalees": 40,
    "pachas": 50, "pachaas": 50, "saath": 60, "sattar": 70, "assi": 80,
    "nabbe": 90, "sau": 100, "aadha": 0.5, "dedh": 1.5, "dhai": 2.5, "sava": 1.25,
    "saade": 0.5,
    # Devanagari
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6, "छः": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "तेरह": 13,
    "चौदह": 14, "पंद्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19,
    "बीस": 20, "पच्चीस": 25, "तीस": 30, "चालीस": 40, "पचास": 50, "साठ": 60,
    "सत्तर": 70, "अस्सी": 80, "नब्बे": 90, "सौ": 100, "आधा": 0.5, "डेढ़": 1.5,
    "ढाई": 2.5, "सवा": 1.25, "साढ़े": 0.5,
}


BOUNDARY_OPEN = "(?<![\\w\u0900-\u097F])"
BOUNDARY_CLOSE = "(?![\\w\u0900-\u097F])"


@dataclass
class TranscriptFacts:
    """Only what the artisan actually said."""

    raw: str = ""
    language: str = "hi"
    colours: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    techniques: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    craft_scores: dict[str, float] = field(default_factory=dict)
    size: str | None = None
    weight: str | None = None
    quantity: int | None = None
    making_days: float | None = None
    making_hours: float | None = None
    expected_price: float | None = None
    care: list[str] = field(default_factory=list)
    product_noun: str | None = None
    mentions_handmade: bool = False
    mentions_natural_dye: bool = False
    word_count: int = 0
    completeness: int = 0
    missing_fields: list[str] = field(default_factory=list)


PRODUCT_NOUNS = {
    "saree": "Saree", "sari": "Saree", "sadi": "Saree", "साड़ी": "Saree",
    "dupatta": "Dupatta", "दुपट्टा": "Dupatta", "stole": "Stole", "scarf": "Scarf",
    "shawl": "Shawl", "shaal": "Shawl", "शॉल": "Shawl",
    "kurta": "Kurta", "कुर्ता": "Kurta", "kurti": "Kurti", "suit": "Suit Set",
    "painting": "Painting", "चित्र": "Painting", "पेंटिंग": "Painting", "art": "Artwork",
    "vase": "Vase", "गुलदस्ता": "Vase", "pot": "Pot", "matka": "Pot", "मटका": "Pot",
    "bowl": "Bowl", "katori": "Bowl", "कटोरी": "Bowl", "plate": "Plate", "थाली": "Plate",
    "diya": "Diya", "दीया": "Diya", "lamp": "Lamp", "लैंप": "Lamp",
    "toy": "Toy", "khilona": "Toy", "खिलौना": "Toy",
    "basket": "Basket", "tokri": "Basket", "टोकरी": "Basket",
    "bag": "Bag", "thaila": "Bag", "थैला": "Bag", "jhola": "Bag",
    "earring": "Earrings", "jhumka": "Jhumka", "झुमका": "Jhumka",
    "necklace": "Necklace", "haar": "Necklace", "हार": "Necklace",
    "bangle": "Bangles", "chudi": "Bangles", "चूड़ी": "Bangles",
    "idol": "Idol", "murti": "Idol", "मूर्ति": "Idol", "figurine": "Figurine",
    "quilt": "Quilt", "razai": "Quilt", "रज़ाई": "Quilt", "throw": "Throw",
    "cushion": "Cushion Cover", "runner": "Table Runner", "rug": "Rug", "carpet": "Carpet",
    "box": "Storage Box", "dabba": "Storage Box", "डिब्बा": "Storage Box",
    "mask": "Mask", "मुखौटा": "Mask", "wall hanging": "Wall Hanging",
}


PRODUCT_NOUNS.update(regional.all_values(regional.NOUNS))
HINDI_NUMBERS.update(regional.all_values(regional.NUMBERS))
for _native, _english in regional.all_values(regional.UNITS).items():
    UNIT_MAP[_native] = {"day": "day", "hour": "hour"}.get(_english, _english)


def detect_language(text: str, hint: str | None = None) -> str:
    """Which of the supported languages this transcript is in.

    Delegates to the script detector, which reads Unicode blocks first and
    only falls back to marker words for romanised input or for the two scripts
    that carry more than one language.
    """
    return detect_script_language(text, hint=hint)


def _find_vocab(text: str, vocab: dict[str, str]) -> list[str]:
    """Canonical values, ordered by where they appear in the sentence.

    Order matters: in "red aur golden design", red is the main colour and gold
    is the accent, and the listing title has to keep that reading.
    """
    hits: list[tuple[int, str]] = []
    low = f" {text.lower()} "
    for word, canonical in vocab.items():
        pattern = re.escape(word.lower())
        m = re.search(BOUNDARY_OPEN + pattern + BOUNDARY_CLOSE, low)
        if m:
            hits.append((m.start(), canonical))
    hits.sort(key=lambda h: h[0])
    ordered: list[str] = []
    for _, canonical in hits:
        if canonical not in ordered:
            ordered.append(canonical)
    return ordered


def _number_before(text: str, units: str) -> tuple[float, str] | None:
    """Match '5.5 metre', 'saade paanch meter', '450 gram', '2 kg'."""
    m = re.search(rf"(\d+(?:[.,]\d+)?)\s*({units})\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ".")), m.group(2).lower()
    words = "|".join(re.escape(w) for w in HINDI_NUMBERS)
    # "chaar sau gram" is four HUNDRED grams, not four and not a hundred.
    m = re.search(
        rf"({words})\s+(sau|सौ|hundred)\s+({units})", text, re.IGNORECASE
    )
    if m:
        return float(HINDI_NUMBERS.get(m.group(1).lower(), 1) * 100), m.group(3).lower()
    # "saade paanch metre" is five-and-a-half metres: the modifier precedes
    # the number it adjusts, so match the pair before matching a bare number.
    m = re.search(
        rf"(saade|saadhe|साढ़े|sava|सवा)\s+({words})\s+({units})", text, re.IGNORECASE
    )
    if m:
        base = HINDI_NUMBERS.get(m.group(2).lower(), 0)
        bump = 0.25 if m.group(1).lower() in ("sava", "सवा") else 0.5
        return float(base + bump), m.group(3).lower()
    m = re.search(rf"({words})\s+({units})", text, re.IGNORECASE)
    if m:
        return float(HINDI_NUMBERS[m.group(1).lower()]), m.group(2).lower()
    return None


def extract_size(text: str) -> str | None:
    # explicit dimension pair first: "24 x 36 inch"
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:x|by|into|\*|×)\s*(\d+(?:\.\d+)?)\s*"
        r"(inch|inches|cm|feet|ft|मीटर|इंच)?",
        text, re.IGNORECASE,
    )
    if m:
        unit = UNIT_MAP.get((m.group(3) or "inch").lower(), "inch")
        return f"{m.group(1)} x {m.group(2)} {unit}"
    length_words = "|".join(
        [r"metre", r"meter", r"mtr", "मीटर", r"inch", r"inches", "इंच", r"cm",
         r"feet", r"foot", r"ft", "फुट"]
        + [w for w, e in regional.all_values(regional.UNITS).items()
           if e in ("metre", "inch", "feet", "cm")])
    hit = _number_before(text, length_words)
    if hit:
        value, unit = hit
        pretty = UNIT_MAP.get(unit, unit)
        value_s = f"{value:g}"
        return f"{value_s} {pretty}"
    return None


def extract_weight(text: str) -> str | None:
    weight_words = "|".join(
        [r"gram", r"gm", r"grams", "ग्राम", r"kg", r"kilo", r"kilogram", "किलो"]
        + [w for w, e in regional.all_values(regional.UNITS).items() if e in ("gram", "kg")])
    hit = _number_before(text, weight_words)
    if hit:
        value, unit = hit
        pretty = UNIT_MAP.get(unit, unit)
        return f"{value:g} {pretty}"
    return None


def extract_making_time(text: str) -> tuple[float | None, float | None]:
    """Returns (days, hours). Labour time is the single biggest price driver."""
    days = hours = None
    day_words = "|".join(
        [r"din", r"days", r"day", "दिन"]
        + [w for w, e in regional.all_values(regional.UNITS).items() if e == "day"])
    hit = _number_before(text, day_words)
    if hit:
        days = hit[0]
    hour_words = "|".join(
        [r"ghante", r"ghanta", r"hours", r"hour", r"hrs", "घंटे", "घंटा"]
        + [w for w, e in regional.all_values(regional.UNITS).items() if e == "hour"])
    hit = _number_before(text, hour_words)
    if hit:
        hours = hit[0]
    hit = _number_before(text, r"hafte|hafta|weeks|week|सप्ताह|हफ़्ते|हफ्ते")
    if hit:
        days = (days or 0) + hit[0] * 7
    hit = _number_before(text, r"mahine|mahina|months|month|महीने|महीना")
    if hit:
        days = (days or 0) + hit[0] * 30
    return days, hours


def extract_quantity(text: str) -> int | None:
    m = re.search(
        r"(\d+)\s*(?:piece|pieces|pcs|nag|adad|items?|टुकड़े|नग|पीस)\b", text, re.IGNORECASE
    )
    if m:
        return int(m.group(1))
    return None


def extract_expected_price(text: str) -> float | None:
    m = re.search(
        r"(?:rs\.?|inr|rupees|rupaye|rupay|रुपये|रुपए|₹)\s*(\d{2,7})", text, re.IGNORECASE
    )
    if m:
        return float(m.group(1))
    m = re.search(
        r"(\d{2,7})\s*(?:rs\.?|rupees|rupaye|rupay|रुपये|रुपए|₹)", text, re.IGNORECASE
    )
    if m:
        return float(m.group(1))
    return None


def score_crafts(text: str) -> dict[str, float]:
    """Keyword evidence for each craft, normalised 0-1."""
    low = f" {text.lower()} "
    scores: dict[str, float] = {}
    for craft in CRAFTS:
        hits = 0.0
        for kw in craft.keywords:
            k = kw.lower()
            if re.search(rf"(?<![\wऀ-ॿ]){re.escape(k)}(?![\wऀ-ॿ])", low):
                # multi-word and craft-name keywords are far stronger evidence
                hits += 2.5 if (" " in k or k in craft.name.lower()) else 1.0
        if hits:
            scores[craft.key] = round(min(1.0, hits / 5.0), 3)
    return scores


def extract(text: str, hint: str | None = None) -> TranscriptFacts:
    """Pull the facts out of whatever language the artisan spoke.

    `hint` is the language they picked in the app; it settles cases the script
    alone cannot, such as Marathi versus Hindi in a short Devanagari phrase.
    """
    text = (text or "").strip()
    facts = TranscriptFacts(raw=text, word_count=len(text.split()))
    if not text:
        facts.missing_fields = ["description", "material", "colour", "size", "making time"]
        return facts

    facts.language = detect_language(text, hint)
    facts.colours = _find_vocab(text, COLOUR_WORDS)
    facts.materials = _find_vocab(text, MATERIAL_WORDS)
    facts.techniques = _find_vocab(text, TECHNIQUE_WORDS)
    facts.regions = _find_vocab(text, REGION_WORDS)
    facts.craft_scores = score_crafts(text)
    facts.size = extract_size(text)
    facts.weight = extract_weight(text)
    facts.quantity = extract_quantity(text)
    facts.making_days, facts.making_hours = extract_making_time(text)
    facts.expected_price = extract_expected_price(text)

    low = text.lower()
    for pattern, label in CARE_PATTERNS:
        if re.search(pattern, low):
            if label not in facts.care:
                facts.care.append(label)

    nouns = _find_vocab(text, PRODUCT_NOUNS)
    facts.product_noun = nouns[0] if nouns else None

    facts.mentions_handmade = bool(
        re.search(r"haath se|हाथ से|hand\s*made|handmade|hath se|swayam|खुद", low)
    )
    facts.mentions_natural_dye = bool(
        re.search(r"natural dye|prakritik rang|प्राकृतिक रंग|herbal|vegetable dye|sabzi rang", low)
    )

    missing = []
    if not facts.materials:
        missing.append("material")
    if not facts.colours:
        missing.append("colour")
    if not facts.size:
        missing.append("size")
    if facts.making_days is None and facts.making_hours is None:
        missing.append("making time")
    if not facts.regions:
        missing.append("place of origin")
    facts.missing_fields = missing
    facts.completeness = max(0, 100 - len(missing) * 18 - (12 if facts.word_count < 12 else 0))
    return facts


def best_craft(facts: TranscriptFacts) -> Craft | None:
    if not facts.craft_scores:
        return None
    key = max(facts.craft_scores, key=lambda k: facts.craft_scores[k])
    from .taxonomy import CRAFT_INDEX

    return CRAFT_INDEX.get(key)
