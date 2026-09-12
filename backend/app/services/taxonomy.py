"""Craft taxonomy — the domain knowledge PAVHAN reasons over.

Each entry carries the vocabulary used to *recognise* the craft (keywords in
English, Hinglish and Devanagari), plus the economics used to *price* it
(material rate, labour hours, skill band, GI status) and the visual signature
used to cross-check an uploaded photograph.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Craft:
    key: str
    name: str
    name_hi: str
    category: str
    default_material: str
    regions: list[str]
    gi_tagged: bool = False
    # recognition
    keywords: list[str] = field(default_factory=list)
    # visual signature used to cross-check the photo
    colour_affinity: list[str] = field(default_factory=list)
    silhouettes: list[str] = field(default_factory=list)
    surfaces: list[str] = field(default_factory=list)
    # economics (INR)
    material_cost: float = 400
    labour_hours: float = 10
    skill_band: str = "skilled"  # apprentice | skilled | master | heritage
    unit: str = "piece"
    typical_weight: str = ""
    care: str = "Handle with care. Store in a dry place."
    care_hi: str = "सावधानी से रखें। सूखी जगह पर रखें।"
    story_hook: str = ""
    export_demand: int = 60  # 0-100
    seo_terms: list[str] = field(default_factory=list)


CRAFTS: list[Craft] = [
    Craft(
        key="banarasi_silk",
        name="Banarasi Handloom Silk",
        name_hi="बनारसी रेशम",
        category="Textiles",
        default_material="Pure Silk",
        regions=["Varanasi", "Banaras", "Uttar Pradesh"],
        gi_tagged=True,
        keywords=["banarasi", "banaras", "varanasi", "silk", "saree", "sari", "sadi",
                  "resham", "zari", "brocade", "बनारसी", "रेशम", "साड़ी", "ज़री"],
        colour_affinity=["Red", "Maroon", "Gold", "Magenta", "Purple", "Green"],
        silhouettes=["wide-textile", "object"],
        surfaces=["woven"],
        material_cost=3200, labour_hours=90, skill_band="heritage",
        unit="saree", typical_weight="450-700 gram",
        care="Dry clean only. Wrap in a cotton muslin cloth and re-fold every few months.",
        care_hi="केवल ड्राई क्लीन। सूती कपड़े में लपेटकर रखें और कुछ महीनों में तह बदलें।",
        story_hook="woven on a pit loom in the lanes of Varanasi, where the zari motifs "
                   "are still read from hand-punched jacquard cards",
        export_demand=88,
        seo_terms=["banarasi saree", "pure silk saree", "handloom zari", "bridal saree",
                   "gi tagged silk", "wedding saree india"],
    ),
    Craft(
        key="pashmina",
        name="Kashmiri Pashmina",
        name_hi="कश्मीरी पश्मीना",
        category="Textiles",
        default_material="Pashmina Wool",
        regions=["Srinagar", "Kashmir", "Jammu and Kashmir"],
        gi_tagged=True,
        keywords=["pashmina", "kashmiri", "kashmir", "shawl", "stole", "cashmere",
                  "sozni", "kani", "पश्मीना", "शॉल", "कश्मीरी"],
        colour_affinity=["Cream", "Beige", "Grey", "Navy", "Maroon", "Olive"],
        silhouettes=["wide-textile"],
        surfaces=["woven"],
        material_cost=4500, labour_hours=120, skill_band="heritage",
        unit="shawl", typical_weight="180-260 gram",
        care="Dry clean only. Never wring. Store flat with a cedar block.",
        care_hi="केवल ड्राई क्लीन। निचोड़ें नहीं। सीधा रखकर संभालें।",
        story_hook="spun from Changthangi goat fleece gathered at 14,000 feet in Ladakh",
        export_demand=94,
        seo_terms=["pashmina shawl", "cashmere wrap", "sozni embroidery", "kashmiri stole"],
    ),
    Craft(
        key="blue_pottery",
        name="Jaipur Blue Pottery",
        name_hi="जयपुर ब्लू पॉटरी",
        category="Pottery & Ceramics",
        default_material="Quartz Ceramic",
        regions=["Jaipur", "Rajasthan"],
        gi_tagged=True,
        keywords=["blue pottery", "jaipur", "ceramic", "vase", "plate", "quartz",
                  "neeli", "नीली", "मिट्टी", "जयपुर", "बर्तन"],
        colour_affinity=["Blue", "Turquoise", "White", "Teal", "Navy"],
        silhouettes=["round-vessel", "tall-vessel"],
        surfaces=["glazed"],
        material_cost=320, labour_hours=14, skill_band="skilled",
        unit="piece", typical_weight="400-900 gram",
        care="Hand wash with a soft cloth. Not microwave safe. Avoid thermal shock.",
        care_hi="मुलायम कपड़े से हाथ से साफ़ करें। माइक्रोवेव में न रखें।",
        story_hook="fired at low heat from quartz paste rather than clay — a Turko-Persian "
                   "technique that reached Jaipur through Mughal court workshops",
        export_demand=76,
        seo_terms=["jaipur blue pottery", "ceramic vase handmade", "blue white pottery india"],
    ),
    Craft(
        key="terracotta",
        name="Terracotta Pottery",
        name_hi="टेराकोटा",
        category="Pottery & Ceramics",
        default_material="Terracotta Clay",
        regions=["Bankura", "West Bengal", "Gorakhpur", "Tamil Nadu"],
        keywords=["terracotta", "clay", "mitti", "matka", "diya", "horse", "pot",
                  "kumhar", "मिट्टी", "टेराकोटा", "मटका", "दीया"],
        colour_affinity=["Terracotta", "Rust", "Brown", "Orange", "Beige"],
        silhouettes=["round-vessel", "tall-vessel", "object"],
        surfaces=["matte", "carved"],
        material_cost=90, labour_hours=8, skill_band="skilled",
        unit="piece", typical_weight="500 gram - 3 kg",
        care="Wipe with a dry cloth. Season with water before first use if it is a vessel.",
        care_hi="सूखे कपड़े से पोंछें। बर्तन है तो पहले उपयोग से पहले पानी में भिगोएँ।",
        story_hook="hand-thrown on a kick wheel and open-fired in a straw kiln",
        export_demand=58,
        seo_terms=["terracotta decor", "handmade clay pot", "bankura horse", "eco pottery"],
    ),
    Craft(
        key="madhubani",
        name="Madhubani Painting",
        name_hi="मधुबनी चित्रकला",
        category="Folk Art",
        default_material="Handmade Paper",
        regions=["Madhubani", "Mithila", "Bihar"],
        gi_tagged=True,
        keywords=["madhubani", "mithila", "painting", "folk art", "chitra", "canvas",
                  "मधुबनी", "मिथिला", "चित्र", "पेंटिंग"],
        colour_affinity=["Red", "Yellow", "Black", "Green", "Orange", "Magenta"],
        silhouettes=["flat-art", "object"],
        surfaces=["painted"],
        material_cost=260, labour_hours=22, skill_band="master",
        unit="painting", typical_weight="80-300 gram",
        care="Keep away from direct sunlight and moisture. Frame under glass.",
        care_hi="सीधी धूप और नमी से बचाएँ। शीशे के फ्रेम में लगाएँ।",
        story_hook="painted with bamboo twigs and natural pigments in a tradition passed "
                   "from mother to daughter on the walls of Mithila homes",
        export_demand=72,
        seo_terms=["madhubani art", "mithila painting", "indian folk art", "tribal wall art"],
    ),
    Craft(
        key="pattachitra",
        name="Pattachitra Scroll Painting",
        name_hi="पट्टचित्र",
        category="Folk Art",
        default_material="Treated Cloth Canvas",
        regions=["Raghurajpur", "Puri", "Odisha"],
        gi_tagged=True,
        keywords=["pattachitra", "patachitra", "odisha", "puri", "scroll", "jagannath",
                  "पट्टचित्र", "ओडिशा"],
        colour_affinity=["Red", "Yellow", "Black", "White", "Green"],
        silhouettes=["flat-art", "wide-textile"],
        surfaces=["painted"],
        material_cost=340, labour_hours=30, skill_band="master",
        unit="painting", typical_weight="150-400 gram",
        care="Do not fold. Roll with tissue if storing. Keep dry.",
        care_hi="मोड़ें नहीं। कागज़ के साथ गोल लपेटकर रखें।",
        story_hook="painted on cloth stiffened with tamarind paste, using stone and shell "
                   "pigments ground by the artist's own family",
        export_demand=68,
        seo_terms=["pattachitra painting", "odisha art", "jagannath art", "scroll painting"],
    ),
    Craft(
        key="dhokra",
        name="Dhokra Metal Craft",
        name_hi="ढोकरा धातु शिल्प",
        category="Metalwork",
        default_material="Brass / Bell Metal",
        regions=["Bastar", "Chhattisgarh", "Jharkhand", "West Bengal"],
        gi_tagged=True,
        keywords=["dhokra", "dokra", "bastar", "brass", "bell metal", "tribal metal",
                  "pital", "ढोकरा", "पीतल", "धातु"],
        colour_affinity=["Gold", "Copper", "Brown", "Charcoal", "Olive"],
        silhouettes=["ornament", "tall-vessel", "object"],
        surfaces=["carved", "matte"],
        material_cost=780, labour_hours=26, skill_band="master",
        unit="figurine", typical_weight="300 gram - 2 kg",
        care="Dust with a dry brush. Occasional wax polish keeps the patina even.",
        care_hi="सूखे ब्रश से धूल हटाएँ। कभी-कभी मोम पॉलिश करें।",
        story_hook="cast by the 4,000-year-old lost-wax method — every piece breaks its own "
                   "mould, so no two can ever be identical",
        export_demand=80,
        seo_terms=["dhokra art", "lost wax brass", "tribal metal figurine", "bastar craft"],
    ),
    Craft(
        key="bidriware",
        name="Bidriware Inlay",
        name_hi="बिदरी कला",
        category="Metalwork",
        default_material="Zinc Alloy with Silver Inlay",
        regions=["Bidar", "Karnataka"],
        gi_tagged=True,
        keywords=["bidri", "bidriware", "bidar", "inlay", "silver inlay", "बिदरी"],
        colour_affinity=["Black", "Charcoal", "Silver", "Grey"],
        silhouettes=["round-vessel", "tall-vessel", "ornament"],
        surfaces=["carved", "glazed"],
        material_cost=1100, labour_hours=34, skill_band="heritage",
        unit="piece", typical_weight="250 gram - 1.5 kg",
        care="Wipe with a dry cloth only. Never use metal polish on the black oxide.",
        care_hi="केवल सूखे कपड़े से पोंछें। पॉलिश का प्रयोग न करें।",
        story_hook="blackened with soil taken from the unlit inner walls of Bidar fort — "
                   "a chemistry no workshop outside Bidar has been able to copy",
        export_demand=74,
        seo_terms=["bidriware", "silver inlay art", "black metal craft india"],
    ),
    Craft(
        key="channapatna",
        name="Channapatna Wooden Toys",
        name_hi="चन्नापटना खिलौने",
        category="Wood Craft",
        default_material="Ivory Wood with Lac",
        regions=["Channapatna", "Karnataka"],
        gi_tagged=True,
        keywords=["channapatna", "wooden toy", "toy", "lacquer", "lac", "khilona",
                  "wood", "lakdi", "खिलौना", "लकड़ी", "चन्नापटना"],
        colour_affinity=["Red", "Yellow", "Green", "Orange", "Turquoise", "Cream"],
        silhouettes=["ornament", "object", "round-vessel"],
        surfaces=["glazed", "matte"],
        material_cost=140, labour_hours=6, skill_band="skilled",
        unit="toy", typical_weight="60-400 gram",
        care="Wipe with a damp cloth. Colours are food-grade vegetable lac — child safe.",
        care_hi="गीले कपड़े से पोंछें। रंग प्राकृतिक और बच्चों के लिए सुरक्षित हैं।",
        story_hook="turned on a hand lathe and polished with lac and a screw-pine leaf, "
                   "using dyes safe enough for a child to mouth",
        export_demand=82,
        seo_terms=["channapatna toys", "wooden toys india", "non toxic toys", "lacquer toys"],
    ),
    Craft(
        key="chikankari",
        name="Lucknawi Chikankari",
        name_hi="लखनवी चिकनकारी",
        category="Textiles",
        default_material="Cotton / Mulmul",
        regions=["Lucknow", "Uttar Pradesh"],
        gi_tagged=True,
        keywords=["chikankari", "chikan", "lucknow", "lucknawi", "kurta", "embroidery",
                  "mulmul", "चिकनकारी", "लखनऊ", "कढ़ाई", "कुर्ता"],
        colour_affinity=["White", "Cream", "Beige", "Pink", "Turquoise", "Grey"],
        silhouettes=["wide-textile", "object"],
        surfaces=["woven", "matte"],
        material_cost=650, labour_hours=45, skill_band="master",
        unit="garment", typical_weight="200-400 gram",
        care="Hand wash in cold water with mild detergent. Dry in shade.",
        care_hi="ठंडे पानी में हल्के साबुन से हाथ से धोएँ। छाँव में सुखाएँ।",
        story_hook="shadow-worked from the reverse of the fabric so the motif seems to float "
                   "under the muslin rather than sit on it",
        export_demand=79,
        seo_terms=["chikankari kurta", "lucknow embroidery", "white on white embroidery"],
    ),
    Craft(
        key="kalamkari",
        name="Kalamkari Hand Painting",
        name_hi="कलमकारी",
        category="Textiles",
        default_material="Natural-Dyed Cotton",
        regions=["Srikalahasti", "Machilipatnam", "Andhra Pradesh"],
        gi_tagged=True,
        keywords=["kalamkari", "kalam", "block print", "natural dye", "andhra",
                  "कलमकारी", "छपाई"],
        colour_affinity=["Rust", "Indigo", "Mustard", "Black", "Cream", "Olive"],
        silhouettes=["wide-textile", "flat-art"],
        surfaces=["painted", "woven"],
        material_cost=520, labour_hours=38, skill_band="master",
        unit="panel", typical_weight="250-500 gram",
        care="First wash separately in cold water. Natural dyes soften beautifully with age.",
        care_hi="पहली बार अलग से ठंडे पानी में धोएँ। प्राकृतिक रंग समय के साथ निखरते हैं।",
        story_hook="drawn with a tamarind-twig pen and coloured only with myrobalan, indigo "
                   "and rusted-iron liquor — a seventeen-step process with no chemicals",
        export_demand=77,
        seo_terms=["kalamkari fabric", "natural dye cotton", "hand painted textile india"],
    ),
    Craft(
        key="phulkari",
        name="Phulkari Embroidery",
        name_hi="फुलकारी",
        category="Textiles",
        default_material="Khaddar Cotton with Silk Floss",
        regions=["Patiala", "Punjab"],
        gi_tagged=True,
        keywords=["phulkari", "punjab", "dupatta", "bagh", "floss", "फुलकारी", "दुपट्टा"],
        colour_affinity=["Magenta", "Orange", "Yellow", "Red", "Pink", "Green"],
        silhouettes=["wide-textile"],
        surfaces=["woven"],
        material_cost=580, labour_hours=40, skill_band="master",
        unit="dupatta", typical_weight="300-500 gram",
        care="Dry clean preferred. Store folded with tissue between the layers.",
        care_hi="ड्राई क्लीन बेहतर है। तह में कागज़ रखकर संभालें।",
        story_hook="darned from the wrong side of hand-spun khaddar so the silk floss "
                   "catches light differently from every angle",
        export_demand=70,
        seo_terms=["phulkari dupatta", "punjabi embroidery", "bagh phulkari"],
    ),
    Craft(
        key="warli",
        name="Warli Tribal Art",
        name_hi="वारली कला",
        category="Folk Art",
        default_material="Cow-dung Wash on Canvas",
        regions=["Palghar", "Maharashtra"],
        keywords=["warli", "tribal art", "maharashtra", "वारली"],
        colour_affinity=["Brown", "Terracotta", "White", "Beige", "Charcoal"],
        silhouettes=["flat-art", "wide-textile"],
        surfaces=["painted", "matte"],
        material_cost=180, labour_hours=16, skill_band="skilled",
        unit="painting", typical_weight="100-350 gram",
        care="Keep dry and out of direct sun. Dust with a soft dry brush.",
        care_hi="सूखी जगह रखें, धूप से बचाएँ। मुलायम ब्रश से धूल हटाएँ।",
        story_hook="painted only in rice paste on an earth-washed ground, using circles, "
                   "triangles and squares drawn from the tribe's reading of nature",
        export_demand=64,
        seo_terms=["warli painting", "tribal art india", "minimal folk art"],
    ),
    Craft(
        key="bamboo_cane",
        name="Bamboo & Cane Craft",
        name_hi="बाँस और बेंत शिल्प",
        category="Natural Fibre",
        default_material="Treated Bamboo",
        regions=["Assam", "Tripura", "Nagaland", "North East"],
        keywords=["bamboo", "cane", "basket", "wicker", "bans", "assam", "tripura",
                  "बाँस", "बेंत", "टोकरी"],
        colour_affinity=["Beige", "Brown", "Olive", "Cream", "Mustard"],
        silhouettes=["round-vessel", "object", "tall-vessel"],
        surfaces=["woven", "matte"],
        material_cost=120, labour_hours=9, skill_band="skilled",
        unit="piece", typical_weight="150 gram - 1.2 kg",
        care="Keep away from prolonged damp. Wipe with a dry cloth.",
        care_hi="ज़्यादा नमी से बचाएँ। सूखे कपड़े से पोंछें।",
        story_hook="split, cured and woven from a single culm of bamboo harvested after "
                   "the third monsoon, when the fibre is at its strongest",
        export_demand=73,
        seo_terms=["bamboo basket", "cane home decor", "sustainable storage", "eco craft"],
    ),
    Craft(
        key="jute",
        name="Jute & Natural Fibre Craft",
        name_hi="जूट शिल्प",
        category="Natural Fibre",
        default_material="Golden Jute",
        regions=["Kolkata", "West Bengal"],
        keywords=["jute", "burlap", "bag", "sustainable", "eco", "जूट", "थैला"],
        colour_affinity=["Beige", "Mustard", "Brown", "Olive", "Cream"],
        silhouettes=["object", "round-vessel"],
        surfaces=["woven", "matte"],
        material_cost=110, labour_hours=5, skill_band="apprentice",
        unit="piece", typical_weight="200-700 gram",
        care="Spot clean only. Air dry. Do not machine wash.",
        care_hi="केवल दाग वाली जगह साफ़ करें। हवा में सुखाएँ।",
        story_hook="woven from golden fibre retted in the Ganga delta — fully compostable "
                   "at the end of its life",
        export_demand=75,
        seo_terms=["jute bag", "eco friendly tote", "sustainable packaging india"],
    ),
    Craft(
        key="meenakari",
        name="Meenakari Enamel Jewellery",
        name_hi="मीनाकारी",
        category="Jewellery",
        default_material="Brass with Vitreous Enamel",
        regions=["Jaipur", "Rajasthan", "Varanasi"],
        gi_tagged=True,
        keywords=["meenakari", "meena", "enamel", "jewellery", "jewelry", "earring",
                  "necklace", "kundan", "मीनाकारी", "गहना", "आभूषण"],
        colour_affinity=["Green", "Blue", "Red", "Gold", "Turquoise", "White"],
        silhouettes=["ornament", "object"],
        surfaces=["glazed", "carved"],
        material_cost=920, labour_hours=18, skill_band="master",
        unit="piece", typical_weight="20-120 gram",
        care="Keep away from perfume and water. Store in the pouch provided.",
        care_hi="इत्र और पानी से बचाएँ। दिए गए थैले में रखें।",
        story_hook="fired five separate times, once for each colour, because every enamel "
                   "melts at a different temperature",
        export_demand=81,
        seo_terms=["meenakari jewellery", "enamel earrings", "rajasthani jewelry"],
    ),
    Craft(
        key="kantha",
        name="Kantha Running-Stitch Craft",
        name_hi="कांथा",
        category="Textiles",
        default_material="Recycled Cotton Layers",
        regions=["Bolpur", "West Bengal", "Odisha"],
        keywords=["kantha", "quilt", "running stitch", "bengal", "कांथा", "रज़ाई"],
        colour_affinity=["Indigo", "Mustard", "Rust", "Cream", "Pink", "Teal"],
        silhouettes=["wide-textile"],
        surfaces=["woven"],
        material_cost=430, labour_hours=35, skill_band="skilled",
        unit="piece", typical_weight="400 gram - 1.4 kg",
        care="Gentle machine wash cold, inside out. Line dry.",
        care_hi="ठंडे पानी में हल्की धुलाई। उल्टा करके सुखाएँ।",
        story_hook="stitched through layers of worn saris, so the quilt carries the cloth of "
                   "a family's own past inside it",
        export_demand=69,
        seo_terms=["kantha quilt", "recycled textile", "hand stitched throw", "boho bedding"],
    ),
    Craft(
        key="pichwai",
        name="Pichwai Painting",
        name_hi="पिछवाई",
        category="Folk Art",
        default_material="Cotton Cloth with Stone Colours",
        regions=["Nathdwara", "Rajasthan"],
        keywords=["pichwai", "pichhwai", "nathdwara", "krishna", "पिछवाई"],
        colour_affinity=["Green", "Gold", "Blue", "Red", "Black"],
        silhouettes=["flat-art", "wide-textile"],
        surfaces=["painted"],
        material_cost=760, labour_hours=55, skill_band="heritage",
        unit="painting", typical_weight="300-900 gram",
        care="Frame under UV glass. Avoid humid walls.",
        care_hi="यूवी शीशे में फ्रेम करें। नमी वाली दीवार से बचाएँ।",
        story_hook="painted to hang behind the Shrinathji idol, with the season changing the "
                   "subject — lotus for monsoon, cows for autumn",
        export_demand=71,
        seo_terms=["pichwai painting", "krishna art", "nathdwara art", "indian wall art"],
    ),
]

CRAFT_INDEX: dict[str, Craft] = {c.key: c for c in CRAFTS}

# Hourly wage floor by skill band (INR). Deliberately above the local
# piece-rate an artisan is usually offered — PAVHAN prices for dignity first.
SKILL_RATE = {
    "apprentice": 55,
    "skilled": 85,
    "master": 130,
    "heritage": 180,
}

# Regional cost-of-living / craft-cluster premium multipliers.
REGION_PREMIUM = {
    "varanasi": 1.12, "banaras": 1.12, "srinagar": 1.18, "kashmir": 1.18,
    "jaipur": 1.10, "bidar": 1.14, "channapatna": 1.05, "lucknow": 1.08,
    "madhubani": 1.06, "bastar": 1.04, "nathdwara": 1.09, "kolkata": 1.03,
}

MATERIALS = [
    "Pure Silk", "Cotton", "Mulmul", "Pashmina Wool", "Terracotta Clay",
    "Quartz Ceramic", "Brass", "Bell Metal", "Zinc Alloy", "Bamboo", "Cane",
    "Jute", "Wood", "Handmade Paper", "Wool", "Khadi", "Leather", "Stone",
]

CATEGORIES = sorted({c.category for c in CRAFTS})


def craft_by_key(key: str) -> Craft | None:
    return CRAFT_INDEX.get(key)


# ---------------------------------------------------------------------------
# Hindi labels for the data itself.
#
# Translating the UI chrome but leaving "Pottery & Ceramics", "Pure Silk" and
# "Varanasi" in English gives a half-Hindi screen, which reads worse than
# either language on its own. These dictionaries let any data token coming out
# of the API be rendered in the artisan's language.
# ---------------------------------------------------------------------------
CATEGORY_HI = {
    "Textiles": "वस्त्र",
    "Pottery & Ceramics": "मिट्टी और सिरेमिक",
    "Folk Art": "लोक कला",
    "Metalwork": "धातु शिल्प",
    "Jewellery": "आभूषण",
    "Wood Craft": "काष्ठ शिल्प",
    "Natural Fibre": "प्राकृतिक रेशा",
}

MATERIAL_HI = {
    "Pure Silk": "शुद्ध रेशम", "Cotton": "सूती", "Mulmul": "मलमल",
    "Pashmina Wool": "पश्मीना ऊन", "Wool": "ऊन", "Khadi": "खादी",
    "Terracotta Clay": "टेराकोटा मिट्टी", "Quartz Ceramic": "क्वार्ट्ज़ सिरेमिक",
    "Brass": "पीतल", "Bell Metal": "कांसा", "Brass / Bell Metal": "पीतल / कांसा",
    "Zinc Alloy": "जस्ता मिश्र", "Zinc Alloy with Silver Inlay": "जस्ता, चांदी की जड़ाई",
    "Bamboo": "बाँस", "Treated Bamboo": "उपचारित बाँस", "Cane": "बेंत",
    "Jute": "जूट", "Golden Jute": "सुनहरा जूट", "Wood": "लकड़ी",
    "Ivory Wood with Lac": "हाथीदाँत लकड़ी, लाख", "Handmade Paper": "हस्तनिर्मित कागज़",
    "Leather": "चमड़ा", "Stone": "पत्थर", "Silver": "चांदी", "Copper": "तांबा",
    "Canvas": "कैनवास", "Zari": "ज़री", "Linen": "लिनन", "Velvet": "मखमल",
    "Glass": "कांच", "Sea Shell": "सीप", "Coconut Shell": "नारियल खोल",
    "Sabai Grass": "सबाई घास", "Wrought Iron": "लोहा",
    "Cotton / Mulmul": "सूती / मलमल", "Natural-Dyed Cotton": "प्राकृतिक रंगी सूती",
    "Khaddar Cotton with Silk Floss": "खद्दर सूती, रेशमी धागा",
    "Recycled Cotton Layers": "पुनर्चक्रित सूती परतें",
    "Cow-dung Wash on Canvas": "गोबर लेपित कैनवास",
    "Treated Cloth Canvas": "उपचारित कपड़ा",
    "Cotton Cloth with Stone Colours": "सूती कपड़ा, पत्थर के रंग",
    "Brass with Vitreous Enamel": "पीतल, मीना रंग",
}

REGION_HI = {
    "Varanasi": "वाराणसी", "Banaras": "बनारस", "Uttar Pradesh": "उत्तर प्रदेश",
    "Srinagar": "श्रीनगर", "Kashmir": "कश्मीर", "Jammu and Kashmir": "जम्मू-कश्मीर",
    "Jaipur": "जयपुर", "Rajasthan": "राजस्थान", "Jodhpur": "जोधपुर",
    "Udaipur": "उदयपुर", "Nathdwara": "नाथद्वारा", "Bidar": "बीदर",
    "Karnataka": "कर्नाटक", "Channapatna": "चन्नापटना", "Lucknow": "लखनऊ",
    "Madhubani": "मधुबनी", "Mithila": "मिथिला", "Bihar": "बिहार",
    "Bastar": "बस्तर", "Chhattisgarh": "छत्तीसगढ़", "Jharkhand": "झारखंड",
    "West Bengal": "पश्चिम बंगाल", "Kolkata": "कोलकाता", "Bankura": "बांकुड़ा",
    "Bolpur": "बोलपुर", "Assam": "असम", "Tripura": "त्रिपुरा",
    "Nagaland": "नागालैंड", "North East": "पूर्वोत्तर", "Punjab": "पंजाब",
    "Patiala": "पटियाला", "Odisha": "ओडिशा", "Puri": "पुरी",
    "Raghurajpur": "रघुराजपुर", "Palghar": "पालघर", "Maharashtra": "महाराष्ट्र",
    "Andhra Pradesh": "आंध्र प्रदेश", "Srikalahasti": "श्रीकालहस्ति",
    "Machilipatnam": "मछलीपट्टनम", "Tamil Nadu": "तमिलनाडु",
    "Gorakhpur": "गोरखपुर", "Kutch": "कच्छ", "Gujarat": "गुजरात",
    "Bhagalpur": "भागलपुर", "Moradabad": "मुरादाबाद", "Agra": "आगरा",
    "Delhi": "दिल्ली", "India": "भारत",
}

ORG_TYPE_HI = {
    "Retail Chain": "खुदरा शृंखला", "Export House": "निर्यात गृह",
    "Hospitality": "होटल उद्योग", "Online Marketplace": "ऑनलाइन बाज़ार",
    "Social Enterprise": "सामाजिक संस्था", "Boutique": "बुटीक",
    "Corporate Gifting": "कॉर्पोरेट उपहार", "Institution": "संस्थान",
}

TECHNIQUE_HI = {
    "Handwoven": "हाथ से बुना", "Handloom": "हथकरघा", "Hand-painted": "हाथ से चित्रित",
    "Hand Embroidery": "हाथ की कढ़ाई", "Hand-carved": "हाथ से तराशा",
    "Block Printed": "ब्लॉक छपाई", "Hand-moulded": "हाथ से ढाला",
    "Wheel-thrown": "चाक पर बना", "Lost-wax Cast": "मोम विधि से ढला",
    "Zari Work": "ज़री का काम", "Inlay Work": "जड़ाई का काम", "Handmade": "हस्तनिर्मित",
}


def colour_labels() -> dict[str, str]:
    """English -> Hindi colour names, taken from the vision module's anchors."""
    from .vision import COLOUR_ANCHORS

    return {name: name_hi for name, name_hi, _ in COLOUR_ANCHORS}


def label_pack() -> dict[str, dict[str, str]]:
    """Everything the app needs to render API data in Hindi."""
    return {
        "crafts": {c.name: c.name_hi for c in CRAFTS},
        "categories": CATEGORY_HI,
        "materials": MATERIAL_HI,
        "regions": REGION_HI,
        "colours": colour_labels(),
        "org_types": ORG_TYPE_HI,
        "techniques": TECHNIQUE_HI,
    }
