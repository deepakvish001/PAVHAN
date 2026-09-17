"""Ministry of Social Justice and Empowerment: who funds these artisans.

The problem statement's Background is not decoration. "Financial assistance is
provided to establish small-scale manufacturing and handicraft units" describes
concrete lending by MoSJE's development corporations, and the final Impact Goal
— "increasing the average annual income of the target demographic" — is a
number the ministry currently has no way to measure after the money is
disbursed.

That is the gap this module exists for. An artisan links the scheme that
financed their unit, and their real sales on PAVHAN become the evidence of
whether it worked.

The corporations and schemes below are real. The rates and ceilings are
indicative and are labelled as such wherever they are shown, because published
terms change and a prototype must not be mistaken for a sanction letter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Corporation:
    code: str
    name: str
    name_hi: str
    serves: str
    serves_hi: str
    schemes: list[str] = field(default_factory=list)


CORPORATIONS: list[Corporation] = [
    Corporation(
        "NSFDC",
        "National Scheduled Castes Finance and Development Corporation",
        "राष्ट्रीय अनुसूचित जाति वित्त एवं विकास निगम",
        "Scheduled Caste families below double the poverty line",
        "दोगुनी गरीबी रेखा से नीचे अनुसूचित जाति परिवार",
        ["Term Loan", "Micro Credit Finance", "Mahila Samriddhi Yojana",
         "Mahila Kisan Yojana", "Green Business Scheme", "Shilpi Samridhi Yojana"],
    ),
    Corporation(
        "NSKFDC",
        "National Safai Karamcharis Finance and Development Corporation",
        "राष्ट्रीय सफाई कर्मचारी वित्त एवं विकास निगम",
        "Safai Karamcharis, manual scavengers and their dependants",
        "सफाई कर्मचारी, हाथ से मैला ढोने वाले और उनके आश्रित",
        ["Swachhata Udyami Yojana", "Mahila Adhikarita Yojana",
         "Micro Credit Finance", "General Term Loan"],
    ),
    Corporation(
        "NBCFDC",
        "National Backward Classes Finance and Development Corporation",
        "राष्ट्रीय पिछड़ा वर्ग वित्त एवं विकास निगम",
        "Other Backward Classes below double the poverty line",
        "दोगुनी गरीबी रेखा से नीचे अन्य पिछड़ा वर्ग",
        ["Term Loan", "Micro Finance", "Swarnima for Women",
         "New Swarnima", "Shilp Sampada"],
    ),
    Corporation(
        "NDFDC",
        "National Divyangjan Finance and Development Corporation",
        "राष्ट्रीय दिव्यांगजन वित्त एवं विकास निगम",
        "Persons with disabilities with 40% or more disability",
        "40% या अधिक दिव्यांगता वाले व्यक्ति",
        ["Divyangjan Swavalamban", "Vishesh Micro Finance",
         "Divyangjan Shiksha Rin", "Self Employment Loan"],
    ),
    Corporation(
        "DNT",
        "Development and Welfare Board for De-notified, Nomadic and Semi-Nomadic Communities",
        "विमुक्त, घुमंतू एवं अर्ध-घुमंतू समुदाय विकास बोर्ड",
        "De-notified, nomadic and semi-nomadic communities",
        "विमुक्त, घुमंतू और अर्ध-घुमंतू समुदाय",
        ["SEED — Scheme for Economic Empowerment of DNTs"],
    ),
]

CORPORATION_INDEX = {c.code: c for c in CORPORATIONS}

# Skilling and cluster schemes an artisan may have come through. These do not
# lend money but they do produce beneficiaries whose income MoSJE tracks.
SKILLING_SCHEMES = [
    {"code": "PM-DAKSH", "name": "PM Dakshata aur Kushalta Sampann Hitgrahi",
     "name_hi": "पीएम दक्षता और कुशलता संपन्न हितग्राही",
     "note": "Free skilling for SC, OBC, EBC, DNT and Safai Karamchari beneficiaries"},
    {"code": "PM-AJAY", "name": "Pradhan Mantri Anusuchit Jaati Abhyuday Yojana",
     "name_hi": "प्रधानमंत्री अनुसूचित जाति अभ्युदय योजना",
     "note": "Village development, grants-in-aid and hostel components"},
    {"code": "SCA-SCSP", "name": "Special Central Assistance to Scheduled Caste Sub Plan",
     "name_hi": "अनुसूचित जाति उप-योजना को विशेष केंद्रीय सहायता",
     "note": "Income-generating assets for SC families"},
    {"code": "VCF-SC", "name": "Venture Capital Fund for Scheduled Castes",
     "name_hi": "अनुसूचित जाति हेतु उद्यम पूंजी निधि",
     "note": "Equity support for SC entrepreneurs"},
]

SOCIAL_CATEGORIES = [
    {"code": "SC", "name": "Scheduled Caste", "name_hi": "अनुसूचित जाति"},
    {"code": "ST", "name": "Scheduled Tribe", "name_hi": "अनुसूचित जनजाति"},
    {"code": "OBC", "name": "Other Backward Class", "name_hi": "अन्य पिछड़ा वर्ग"},
    {"code": "DNT", "name": "De-notified / Nomadic", "name_hi": "विमुक्त / घुमंतू"},
    {"code": "SK", "name": "Safai Karamchari", "name_hi": "सफाई कर्मचारी"},
    {"code": "PwD", "name": "Person with Disability", "name_hi": "दिव्यांगजन"},
    {"code": "GEN", "name": "Not applicable", "name_hi": "लागू नहीं"},
]

# Indicative terms, shown only to help an artisan see whether their earnings
# can service what they borrowed. Never presented as the sanctioned rate.
INDICATIVE_TERMS = {
    "NSFDC": {"interest": 6.0, "tenure_years": 5, "ceiling": 3000000},
    "NSKFDC": {"interest": 6.0, "tenure_years": 5, "ceiling": 1500000},
    "NBCFDC": {"interest": 6.0, "tenure_years": 5, "ceiling": 1500000},
    "NDFDC": {"interest": 5.0, "tenure_years": 5, "ceiling": 500000},
    "DNT": {"interest": 0.0, "tenure_years": 0, "ceiling": 100000},
}

DISCLAIMER = {
    "en": "Scheme terms shown here are indicative and for planning only. Your "
          "sanctioned rate, tenure and instalment are whatever your loan "
          "document says. PAVHAN does not lend, sanction or recover money.",
    "hi": "यहाँ दी गई शर्तें केवल अनुमान के लिए हैं। आपकी असली ब्याज दर, अवधि और किस्त वही "
          "है जो आपके ऋण दस्तावेज़ में लिखी है। पावहन न ऋण देता है, न वसूली करता है।",
}


def corporations() -> list[dict]:
    out = []
    for c in CORPORATIONS:
        row = asdict(c)
        row["indicative_terms"] = INDICATIVE_TERMS.get(c.code, {})
        out.append(row)
    return out


def monthly_instalment(principal: float, code: str) -> float:
    """Indicative EMI, so an artisan can see it against real monthly earnings."""
    terms = INDICATIVE_TERMS.get(code)
    if not terms or not principal or not terms.get("tenure_years"):
        return 0.0
    months = terms["tenure_years"] * 12
    rate = terms["interest"] / 100 / 12
    if rate <= 0:
        return round(principal / months, 2)
    factor = (1 + rate) ** months
    return round(principal * rate * factor / (factor - 1), 2)
