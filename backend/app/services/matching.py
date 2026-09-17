"""Buyer matching.

The old screen said "select a product to see AI-matched buyer categories" and
then showed nothing, because nothing was actually scored against the product.
Here every buyer is scored on seven weighted signals derived from the product
in front of us, and each match explains itself factor by factor so the artisan
knows *why* this buyer, and what to say to them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

WEIGHTS = {
    "category": 0.26,
    "price_fit": 0.22,
    "capacity": 0.16,
    "material": 0.12,
    "region": 0.10,
    "values": 0.09,
    "reliability": 0.05,
}


@dataclass
class MatchFactor:
    label: str
    label_hi: str
    score: float          # 0-1
    weight: float
    detail: str
    detail_hi: str = ""


@dataclass
class BuyerMatch:
    buyer_id: str
    name: str
    org_type: str
    city: str
    country: str
    logo: str
    score: int                       # 0-100
    fit_label: str
    fit_label_hi: str = ""
    factors: list[MatchFactor] = field(default_factory=list)
    suggested_quantity: int = 0
    suggested_unit_price: float = 0
    estimated_order_value: float = 0
    lead_time_ok: bool = True
    gaps: list[str] = field(default_factory=list)
    gaps_hi: list[str] = field(default_factory=list)
    pitch: str = ""
    pitch_hi: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["factors"] = [asdict(f) if not isinstance(f, dict) else f for f in self.factors]
        return d


def _overlap(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    sa = {x.strip().lower() for x in a if x}
    sb = {x.strip().lower() for x in b if x}
    if not sa or not sb:
        return 0.0
    # partial credit for substring matches ("Pure Silk" vs "Silk")
    hits = 0.0
    for x in sa:
        if x in sb:
            hits += 1.0
        elif any(x in y or y in x for y in sb):
            hits += 0.6
    return min(1.0, hits / len(sa))


def _category_fit(product, buyer) -> tuple[float, str]:
    """How well the buyer's sourcing list covers THIS product.

    Averaging over every tag buries an exact hit: a buyer who literally lists
    "Pottery & Ceramics" must score 1.0 on a pottery listing, not 0.2 because
    the product also carries nine tags they never mentioned.
    """
    cats = {c.strip().lower() for c in (buyer.categories or []) if c}
    if not cats:
        return 0.5, "They have not narrowed their sourcing categories", "इन्होंने कोई श्रेणी तय नहीं की है"

    category = (product.category or "").strip().lower()
    craft = (product.craft_type or "").strip().lower()
    tags = {str(t).strip().lower() for t in (product.tags or []) if t}

    if category and category in cats:
        return 1.0, f"They source {product.category} directly", f"ये सीधे {product.category} ख़रीदते हैं"
    if craft and any(craft in c or c in craft for c in cats):
        return 0.9, "They source this craft family directly", "ये इसी तरह का शिल्प ख़रीदते हैं"
    if category and any(category in c or c in category for c in cats):
        return 0.75, f"Their sourcing list overlaps {product.category}", f"इनकी सूची {product.category} से मिलती है"
    tag_hits = sum(1 for t in tags if t in cats)
    if tag_hits:
        return (min(0.6, 0.3 + tag_hits * 0.15),
                "Some of your product tags match their list",
                "आपके सामान के कुछ लेबल इनकी सूची से मिलते हैं")
    return (0.12, f"They buy {', '.join(buyer.categories[:2])} — a different category",
            f"ये {', '.join(buyer.categories[:2])} ख़रीदते हैं — अलग श्रेणी है")


def _price_fit(price: float, lo: float, hi: float) -> tuple[float, str, str]:
    if price <= 0:
        return 0.4, "Product has no price yet", "इस सामान का दाम अभी तय नहीं है"
    if lo <= price <= hi:
        return (1.0, f"Rs.{price:,.0f} sits inside their Rs.{lo:,.0f}-{hi:,.0f} band",
                f"₹{price:,.0f} इनके ₹{lo:,.0f}–{hi:,.0f} के दायरे में है")
    if price < lo:
        # Below the band is a soft miss — they can bundle it, but it reads cheap.
        ratio = price / max(lo, 1)
        return (max(0.25, ratio), f"Rs.{price:,.0f} is below their usual Rs.{lo:,.0f} floor",
                f"₹{price:,.0f} इनके ₹{lo:,.0f} के न्यूनतम से नीचे है")
    ratio = hi / max(price, 1)
    return (max(0.1, ratio * 0.9), f"Rs.{price:,.0f} is above their Rs.{hi:,.0f} ceiling",
            f"₹{price:,.0f} इनकी ₹{hi:,.0f} की सीमा से ऊपर है")


def _fit_label(score: int) -> tuple[str, str]:
    if score >= 82:
        return "Excellent match", "बहुत अच्छा मेल"
    if score >= 68:
        return "Strong match", "अच्छा मेल"
    if score >= 52:
        return "Worth approaching", "कोशिश करने लायक"
    return "Long shot", "कम संभावना"


def _pitch(product, buyer, qty: int, unit_price: float, top_factor: str) -> tuple[str, str]:
    craft = product.craft_type or product.category or "handmade"
    origin = product.region or "India"
    en = (
        f"Namaste {buyer.name}, I am {getattr(product, '_artisan_name', 'an artisan')} from "
        f"{origin}. I make {craft} {product.title.split('—')[0].strip().lower()} entirely by hand. "
        f"{'This craft carries a GI tag. ' if product.gi_tagged else ''}"
        f"I can supply {qty} pieces at Rs.{unit_price:,.0f} each, ready in "
        f"{product.lead_time_days} days. {top_factor} "
        f"Shall I send you samples and a full catalogue?"
    )
    hi = (
        f"नमस्ते {buyer.name}, मैं {origin} का कारीगर हूँ और {craft} का काम हाथ से करता हूँ। "
        f"मैं {qty} पीस ₹{unit_price:,.0f} प्रति पीस के हिसाब से {product.lead_time_days} दिन में "
        f"दे सकता हूँ। क्या मैं नमूना और पूरी सूची भेजूँ?"
    )
    return en, hi


def match_buyers(product, buyers: list, *, limit: int = 8, min_score: int = 0) -> list[BuyerMatch]:
    """Score every active buyer against one concrete product."""
    results: list[BuyerMatch] = []
    for buyer in buyers:
        if not buyer.active:
            continue
        factors: list[MatchFactor] = []
        gaps: list[str] = []
        gaps_hi: list[str] = []

        cat, cat_detail, cat_detail_hi = _category_fit(product, buyer)
        factors.append(MatchFactor("Category fit", "श्रेणी का मेल", round(cat, 3),
                                   WEIGHTS["category"], cat_detail, cat_detail_hi))
        if cat < 0.3:
            gaps.append("Different product category to what they usually buy")
            gaps_hi.append("ये आमतौर पर दूसरी श्रेणी का सामान लेते हैं")

        pf, pf_detail, pf_detail_hi = _price_fit(product.price, buyer.budget_min, buyer.budget_max)
        factors.append(MatchFactor("Price band", "दाम का दायरा", round(pf, 3),
                                   WEIGHTS["price_fit"], pf_detail, pf_detail_hi))
        if pf < 0.5:
            gaps.append("Price sits outside their normal band")
            gaps_hi.append("दाम इनके सामान्य दायरे से बाहर है")

        # Capacity: can the artisan actually serve this buyer's order size?
        qty = max(buyer.typical_order_qty, product.moq)
        capacity_ok = product.lead_time_days <= buyer.max_lead_time_days
        stock_ratio = min(1.0, max(product.stock, 1) / max(buyer.typical_order_qty, 1))
        capacity = (0.65 if capacity_ok else 0.25) + stock_ratio * 0.35
        factors.append(MatchFactor(
            "Order capacity", "आपकी क्षमता", round(min(capacity, 1.0), 3), WEIGHTS["capacity"],
            f"They order ~{buyer.typical_order_qty} pcs and accept up to "
            f"{buyer.max_lead_time_days} days lead time; yours is {product.lead_time_days} days",
            f"ये लगभग {buyer.typical_order_qty} पीस लेते हैं और {buyer.max_lead_time_days} दिन तक "
            f"इंतज़ार कर सकते हैं; आपको {product.lead_time_days} दिन लगते हैं",
        ))
        if not capacity_ok:
            gaps.append(
                f"Your {product.lead_time_days}-day lead time exceeds their "
                f"{buyer.max_lead_time_days}-day limit"
            )
            gaps_hi.append(
                f"आपके {product.lead_time_days} दिन इनकी {buyer.max_lead_time_days} दिन "
                f"की सीमा से ज़्यादा हैं"
            )

        mat = _overlap([product.material], buyer.materials)
        factors.append(MatchFactor(
            "Material match", "सामग्री का मेल", round(mat, 3), WEIGHTS["material"],
            f"They work with {', '.join(buyer.materials[:3]) or 'any material'}",
            f"ये {', '.join(buyer.materials[:3]) or 'किसी भी सामग्री'} के साथ काम करते हैं",
        ))

        reg = _overlap([product.region], buyer.preferred_regions)
        if not buyer.preferred_regions:
            reg = 0.6
        factors.append(MatchFactor(
            "Sourcing region", "क्षेत्र", round(reg, 3), WEIGHTS["region"],
            f"They prefer {', '.join(buyer.preferred_regions[:3]) or 'pan-India sourcing'}",
            f"इन्हें {', '.join(buyer.preferred_regions[:3]) or 'पूरे भारत'} से लेना पसंद है",
        ))

        values = (
            (product.sustainability_score / 100) * (buyer.values_sustainability / 100) * 0.55
            + (1.0 if product.gi_tagged else 0.35) * (buyer.values_gi_tag / 100) * 0.45
        )
        values = min(1.0, values * 1.6)
        factors.append(MatchFactor(
            "Values & certification", "मूल्य और प्रमाण", round(values, 3), WEIGHTS["values"],
            ("They weight sustainability heavily" if buyer.values_sustainability > 70
             else "Sustainability is a moderate factor for them")
            + (" and prefer GI-tagged craft" if buyer.values_gi_tag > 70 else ""),
            ("ये पर्यावरण को बहुत महत्व देते हैं" if buyer.values_sustainability > 70
             else "पर्यावरण इनके लिए सामान्य महत्व रखता है")
            + (", और जीआई प्रमाणित शिल्प पसंद करते हैं" if buyer.values_gi_tag > 70 else ""),
        ))

        reliability = buyer.repeat_buyer_score / 100
        factors.append(MatchFactor(
            "Buyer reliability", "खरीदार की साख", round(reliability, 3), WEIGHTS["reliability"],
            f"{buyer.repeat_buyer_score}% repeat-order record on PAVHAN",
            f"पावहन पर इनका {buyer.repeat_buyer_score}% दोबारा ऑर्डर देने का रिकॉर्ड है",
        ))

        raw = sum(f.score * f.weight for f in factors)
        score = int(round(raw * 100))

        # Bulk pricing: buyers ordering volume get a graduated discount.
        if qty >= 100:
            unit = product.price * 0.72
        elif qty >= 50:
            unit = product.price * 0.78
        elif qty >= 20:
            unit = product.price * 0.85
        else:
            unit = product.price * 0.92
        unit = round(unit, 0)

        top = max(factors, key=lambda f: f.score * f.weight)
        fit_en, fit_hi = _fit_label(score)
        match = BuyerMatch(
            buyer_id=buyer.id,
            name=buyer.name,
            org_type=buyer.org_type,
            city=buyer.city,
            country=buyer.country,
            logo=buyer.logo,
            score=score,
            fit_label=fit_en,
            fit_label_hi=fit_hi,
            factors=factors,
            suggested_quantity=qty,
            suggested_unit_price=unit,
            estimated_order_value=round(unit * qty, 0),
            lead_time_ok=capacity_ok,
            gaps=gaps,
            gaps_hi=gaps_hi,
        )
        match.pitch, match.pitch_hi = _pitch(product, buyer, qty, unit, top.detail + ".")
        results.append(match)

    results.sort(key=lambda m: m.score, reverse=True)
    return [m for m in results if m.score >= min_score][:limit]


def buyer_categories(matches: list[BuyerMatch]) -> list[dict]:
    """Roll matches up into the buyer-category view the artisan sees first."""
    groups: dict[str, dict] = {}
    for m in matches:
        key = m.org_type
        g = groups.setdefault(key, {
            "category": key, "count": 0, "best_score": 0,
            "total_value": 0.0, "buyers": [],
        })
        g["count"] += 1
        g["best_score"] = max(g["best_score"], m.score)
        g["total_value"] += m.estimated_order_value
        g["buyers"].append({"name": m.name, "score": m.score, "city": m.city})
    ordered = sorted(groups.values(), key=lambda g: g["best_score"], reverse=True)
    for g in ordered:
        g["total_value"] = round(g["total_value"], 0)
    return ordered
