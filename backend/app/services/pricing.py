"""Price recommendation.

Most artisans are paid a piece rate set by a middleman that silently values
their labour at ₹20-30 an hour. PAVHAN builds the price from the other
direction — cost of material, honest hourly wage for the skill band, the
intricacy the camera actually measured, then the market band the product
belongs to — and shows every line of that arithmetic so the artisan can defend
the number in a negotiation.

Output is a floor / recommended / premium band plus an explainable breakdown
and live comparables.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

from .taxonomy import REGION_PREMIUM, SKILL_RATE, Craft

# Marketplace context. Season index reflects observed Indian craft demand:
# the wedding + festival window (Sep-Feb) carries real pricing power.
SEASON_INDEX = {
    1: 1.06, 2: 1.08, 3: 0.98, 4: 0.95, 5: 0.93, 6: 0.92,
    7: 0.95, 8: 1.02, 9: 1.10, 10: 1.18, 11: 1.14, 12: 1.08,
}
SEASON_LABEL_HI = {
    1: "सर्दी की शादियाँ", 2: "शादी का मौसम", 3: "मौसम के बाद",
    4: "कम माँग", 5: "कम माँग", 6: "बरसात की सुस्ती",
    7: "माँग लौट रही है", 8: "राखी और ओणम की माँग", 9: "त्योहारों की तैयारी",
    10: "दिवाली का चरम", 11: "शादी और निर्यात का चरम", 12: "सर्दी का उपहार मौसम",
}

SEASON_LABEL = {
    1: "Winter wedding season", 2: "Wedding season", 3: "Post-season",
    4: "Low season", 5: "Low season", 6: "Monsoon lull",
    7: "Early revival", 8: "Rakhi & Onam demand", 9: "Festive build-up",
    10: "Diwali peak", 11: "Wedding + export peak", 12: "Winter gifting",
}

# What each channel adds on top of the artisan's realisation.
CHANNEL_MARGIN = {
    "direct": 0.10,       # PAVHAN direct-to-customer
    "marketplace": 0.22,  # listed on a large marketplace
    "b2b": 0.08,          # bulk, buyer handles retail
    "export": 0.34,       # export house, includes documentation & freight
}

PACKAGING_BY_CATEGORY = {
    "Textiles": 60, "Pottery & Ceramics": 140, "Folk Art": 90,
    "Metalwork": 110, "Jewellery": 80, "Wood Craft": 70, "Natural Fibre": 50,
}


@dataclass
class PriceLine:
    label: str
    label_hi: str
    amount: float
    note: str = ""
    note_hi: str = ""


@dataclass
class PriceRecommendation:
    floor: float = 0
    recommended: float = 0
    premium: float = 0
    currency: str = "INR"
    artisan_earning: float = 0
    effective_hourly_wage: float = 0
    margin_percent: float = 0
    confidence: int = 0
    breakdown: list[PriceLine] = field(default_factory=list)
    comparables: list[dict] = field(default_factory=list)
    demand_index: float = 1.0
    season_label: str = ""
    season_label_hi: str = ""
    rationale: list[str] = field(default_factory=list)
    rationale_hi: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    warnings_hi: list[str] = field(default_factory=list)
    channel: str = "direct"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["breakdown"] = [asdict(b) if not isinstance(b, dict) else b for b in self.breakdown]
        return d


def _round_price(value: float) -> float:
    """Retail-friendly rounding: ...49 / ...99 endings read as considered."""
    if value < 500:
        return float(int(value / 10) * 10 + 9)
    if value < 5000:
        return float(int(value / 50) * 50 + 49)
    return float(int(value / 100) * 100 + 99)


def _labour_hours(craft: Craft, facts_days: float | None, facts_hours: float | None) -> tuple[float, str]:
    """Prefer what the artisan said; fall back to the craft's typical hours."""
    if facts_hours:
        return facts_hours, "as stated by the artisan"
    if facts_days:
        # A working craft day is ~6 focused hours, not 8.
        return facts_days * 6, f"{facts_days:g} day(s) at 6 working hours"
    return craft.labour_hours, "typical for this craft"


def recommend_price(
    craft: Craft,
    *,
    complexity: float = 1.0,
    making_days: float | None = None,
    making_hours: float | None = None,
    region: str = "",
    skill_band: str | None = None,
    material_cost: float | None = None,
    quality_score: int = 70,
    gi_tagged: bool | None = None,
    natural_dye: bool = False,
    channel: str = "direct",
    quantity: int = 1,
    artisan_expectation: float | None = None,
    labour_cost: float | None = None,
    other_cost: float | None = None,
    desired_margin_percent: float | None = None,
    today: date | None = None,
) -> PriceRecommendation:
    rec = PriceRecommendation(channel=channel)
    today = today or date.today()

    band = skill_band or craft.skill_band
    hourly = SKILL_RATE.get(band, SKILL_RATE["skilled"])
    hours, hours_note = _labour_hours(craft, making_days, making_hours)
    mat_cost = material_cost if material_cost is not None else craft.material_cost
    gi = craft.gi_tagged if gi_tagged is None else gi_tagged

    # --- cost side ---------------------------------------------------------
    complexity = max(0.85, min(complexity, 2.2))
    # A stated labour cost wins over the computed one: the artisan knows what
    # they paid their own hands, or their helper's.
    labour = labour_cost if labour_cost is not None else hours * hourly * complexity
    if labour_cost is not None:
        hours_note = "as entered by the artisan"
    rec.breakdown.append(
        PriceLine("Material", "कच्चा माल", round(mat_cost, 2),
                  f"{craft.default_material}, market rate for one {craft.unit}",
                  f"{craft.default_material} का बाज़ार भाव, एक {craft.unit} के लिए")
    )
    rec.breakdown.append(
        PriceLine(
            "Skilled labour", "कारीगरी",
            round(labour, 2),
            f"{hours:g} hrs x Rs.{hourly}/hr ({band}) x {complexity:g} intricacy — {hours_note}",
            f"{hours:g} घंटे × ₹{hourly}/घंटा ({band}) × {complexity:g} बारीकी",
        )
    )

    region_key = (region or "").strip().lower()
    region_mult = REGION_PREMIUM.get(region_key, 1.0)
    cluster_premium = (mat_cost + labour) * (region_mult - 1)
    if cluster_premium > 0:
        rec.breakdown.append(
            PriceLine("Craft-cluster premium", "क्षेत्र मूल्य", round(cluster_premium, 2),
                      f"{region.title()} cluster commands a {int((region_mult-1)*100)}% premium",
                      f"{region.title()} के शिल्प क्षेत्र का {int((region_mult-1)*100)}% अतिरिक्त मूल्य")
        )

    gi_premium = (mat_cost + labour) * 0.12 if gi else 0
    if gi_premium:
        rec.breakdown.append(
            PriceLine("GI-tag authenticity", "जीआई प्रमाण", round(gi_premium, 2),
                      "Geographical Indication protected craft",
                      "भौगोलिक संकेत से संरक्षित शिल्प")
        )

    dye_premium = (mat_cost + labour) * 0.07 if natural_dye else 0
    if dye_premium:
        rec.breakdown.append(
            PriceLine("Natural-dye premium", "प्राकृतिक रंग", round(dye_premium, 2),
                      "Chemical-free dyeing is a documented buyer preference",
                      "बिना रसायन की रंगाई के लिए खरीदार ज़्यादा देते हैं")
        )

    packaging = other_cost if other_cost is not None else PACKAGING_BY_CATEGORY.get(
        craft.category, 70)
    rec.breakdown.append(
        PriceLine(
            "Other costs" if other_cost is not None else "Packaging & handling",
            "अन्य ख़र्च" if other_cost is not None else "पैकिंग",
            float(packaging),
            "As entered by you" if other_cost is not None
            else "Protective craft-safe packaging",
            "आपके बताए अनुसार" if other_cost is not None
            else "सामान सुरक्षित पहुँचाने की पैकिंग")
    )

    quality_adj = (mat_cost + labour) * ((quality_score - 70) / 100) * 0.35
    if abs(quality_adj) >= 1:
        rec.breakdown.append(
            PriceLine("Listing quality adjustment", "गुणवत्ता समायोजन", round(quality_adj, 2),
                      f"Listing completeness score {quality_score}/100",
                      f"विवरण की पूर्णता {quality_score}/100")
        )

    cost_base = mat_cost + labour + cluster_premium + gi_premium + dye_premium + packaging + quality_adj

    # --- market side -------------------------------------------------------
    demand = SEASON_INDEX.get(today.month, 1.0)
    export_pull = 1 + (craft.export_demand - 60) / 100 * 0.22
    rec.demand_index = round(demand * export_pull, 3)
    rec.season_label = SEASON_LABEL.get(today.month, "")
    rec.season_label_hi = SEASON_LABEL_HI.get(today.month, "")

    margin = (desired_margin_percent / 100 if desired_margin_percent is not None
              else CHANNEL_MARGIN.get(channel, 0.12))
    if quantity >= 50:
        margin *= 0.8  # bulk orders trade margin for volume
    elif quantity >= 20:
        margin *= 0.9

    recommended = cost_base * rec.demand_index * (1 + margin)
    rec.recommended = _round_price(recommended)
    rec.floor = _round_price(cost_base * 1.04)          # never below cost + 4%
    rec.premium = _round_price(recommended * 1.28)      # curated / gifting tier
    rec.margin_percent = round(margin * 100, 1)

    # What the artisan actually takes home on the recommended price.
    platform_fee = rec.recommended * 0.05  # PAVHAN keeps 5%, flat and visible
    rec.artisan_earning = round(rec.recommended - platform_fee - packaging, 2)
    rec.effective_hourly_wage = round(
        (rec.artisan_earning - mat_cost) / max(hours, 0.5), 2
    )

    # --- comparables -------------------------------------------------------
    for label, label_hi, mult, note, note_hi in (
        ("Local trader / middleman rate", "बिचौलिये का भाव", 0.42,
         "What a trader typically pays at your door",
         "बिचौलिया आमतौर पर घर पर आकर इतना देता है"),
        ("Nearby craft-bazaar stall", "पास के हाट का भाव", 0.72,
         "Tourist bazaar retail inside the cluster",
         "क्षेत्र के बाज़ार में इसी का खुदरा दाम"),
        ("Urban boutique shelf price", "शहरी दुकान का दाम", 1.35,
         "Metro boutique with a 2.5x markup",
         "बड़े शहर की दुकान ढाई गुना पर बेचती है"),
        ("Export house FOB", "निर्यात का दाम", 1.62,
         "Export order including certification and freight",
         "निर्यात ऑर्डर, प्रमाणपत्र और भाड़े सहित"),
    ):
        comp = _round_price(rec.recommended * mult)
        rec.comparables.append({
            "label": label,
            "label_hi": label_hi,
            "price": comp,
            "note": note,
            "note_hi": note_hi,
            "delta_percent": round((comp - rec.recommended) / max(rec.recommended, 1) * 100, 1),
        })

    # --- explanation -------------------------------------------------------
    rec.rationale = [
        f"Your {hours:g} hours of work are valued at Rs.{hourly}/hour for a "
        f"{band}-level {craft.name} maker — not at a piece rate.",
        f"The photograph showed {'high' if complexity > 1.35 else 'moderate'} motif intricacy, "
        f"so labour is multiplied by {complexity:g}.",
        f"{rec.season_label} puts the demand index at {rec.demand_index:g}x right now.",
        f"At Rs.{rec.recommended:,.0f} you keep Rs.{rec.artisan_earning:,.0f} — an effective "
        f"Rs.{rec.effective_hourly_wage:,.0f}/hour after material cost.",
    ]
    rec.rationale_hi = [
        f"आपके {hours:g} घंटे के काम को ₹{hourly}/घंटा की दर से जोड़ा गया है।",
        f"फोटो में डिज़ाइन की बारीकी देखकर मेहनत {complexity:g} गुना मानी गई है।",
        f"अभी {rec.season_label_hi} है, इसलिए माँग {rec.demand_index:g} गुना है।",
        f"₹{rec.recommended:,.0f} पर आपको ₹{rec.artisan_earning:,.0f} मिलेंगे।",
    ]

    if artisan_expectation:
        gap = (rec.recommended - artisan_expectation) / max(artisan_expectation, 1) * 100
        if gap > 12:
            rec.warnings.append(
                f"You asked for Rs.{artisan_expectation:,.0f}. Our analysis says this piece is "
                f"worth about {gap:.0f}% more — you are under-pricing your own work."
            )
            rec.warnings_hi.append(
                f"आपने ₹{artisan_expectation:,.0f} माँगा था। हमारे हिसाब से यह लगभग "
                f"{gap:.0f}% और मिलना चाहिए — आप अपनी मेहनत का दाम कम लगा रहे हैं।"
            )
        elif gap < -18:
            rec.warnings.append(
                f"You asked for Rs.{artisan_expectation:,.0f}, which is above the market band. "
                f"It can still sell in the premium tier, but expect a slower turn."
            )
            rec.warnings_hi.append(
                f"आपने ₹{artisan_expectation:,.0f} माँगा है जो बाज़ार भाव से ऊपर है। "
                f"बिकेगा ज़रूर, पर थोड़ा समय लग सकता है।"
            )

    if rec.effective_hourly_wage < 60:
        rec.warnings.append(
            "This price still leaves you under Rs.60/hour. Consider a smaller size or a "
            "batch order so your time is paid fairly."
        )
        rec.warnings_hi.append(
            "इस दाम पर भी आपको ₹60 प्रति घंटे से कम मिल रहा है। थोड़ा छोटा नाप या "
            "एक साथ कई पीस बनाइए ताकि समय का पूरा मोल मिले।"
        )

    # --- confidence --------------------------------------------------------
    confidence = 55
    if making_days or making_hours:
        confidence += 18
    if material_cost is not None:
        confidence += 8
    if quality_score >= 80:
        confidence += 10
    if gi:
        confidence += 5
    rec.confidence = min(96, confidence)
    return rec
