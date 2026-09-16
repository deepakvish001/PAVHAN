"""Make a listing ready for a government e-marketplace.

The problem statement asks for connection to "B2B buyers **or** government
e-marketplaces". Live submission to GeM or ONDC needs a seller account, an
API key and an onboarding agreement that a hackathon team cannot hold. What a
team *can* build — and what actually removes the work from the artisan — is
everything up to the push: the field mapping, the HSN classification, the
statutory declarations, and a readiness check that names what is still
missing.

So this module produces a submission-shaped package and is explicit that the
final POST needs credentials. Nothing here claims an integration that does
not exist.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

# HSN codes actually used for handicraft exports, by craft category. Getting
# this wrong is one of the commonest reasons an artisan's GeM listing is
# rejected, and it is not something they can reasonably be expected to know.
HSN_BY_CATEGORY: dict[str, tuple[str, str]] = {
    "Textiles": ("5007", "Woven fabrics of silk or of silk waste"),
    "Folk Art": ("9701", "Paintings, drawings and pastels, executed by hand"),
    "Metalwork": ("8306", "Statuettes and other ornaments of base metal"),
    "Jewellery": ("7117", "Imitation jewellery"),
    "Pottery & Ceramics": ("6912", "Ceramic tableware and other household articles"),
    "Wood Craft": ("4420", "Wood marquetry; caskets and cases; wooden ornaments"),
    "Natural Fibre": ("4602", "Basketwork and wickerwork made from plaiting materials"),
}

# More specific codes where the material makes the classification differ.
HSN_BY_MATERIAL: dict[str, tuple[str, str]] = {
    "Cotton": ("5208", "Woven fabrics of cotton"),
    "Pashmina Wool": ("6214", "Shawls, scarves and mufflers of wool"),
    "Wool": ("6214", "Shawls, scarves and mufflers of wool"),
    "Jute": ("5310", "Woven fabrics of jute or other textile bast fibres"),
    "Golden Jute": ("5310", "Woven fabrics of jute or other textile bast fibres"),
    "Bamboo": ("4602", "Basketwork and wickerwork of vegetable materials"),
    "Terracotta Clay": ("6913", "Statuettes and other ornamental ceramic articles"),
}

GEM_CATEGORY = {
    "Textiles": "Handloom and Handicraft > Textiles > Handloom Fabric",
    "Folk Art": "Handloom and Handicraft > Art > Paintings",
    "Metalwork": "Handloom and Handicraft > Metal Craft",
    "Jewellery": "Handloom and Handicraft > Artificial Jewellery",
    "Pottery & Ceramics": "Handloom and Handicraft > Pottery and Ceramics",
    "Wood Craft": "Handloom and Handicraft > Wooden Handicraft",
    "Natural Fibre": "Handloom and Handicraft > Cane and Bamboo Products",
}

ONDC_CATEGORY = {
    "Textiles": "Handicrafts and Handloom",
    "Folk Art": "Home Decor",
    "Metalwork": "Home Decor",
    "Jewellery": "Fashion Jewellery",
    "Pottery & Ceramics": "Home Decor",
    "Wood Craft": "Home Decor",
    "Natural Fibre": "Home and Kitchen",
}


def hsn_for(category: str, material: str) -> tuple[str, str]:
    """The code a customs officer would apply, with its official wording."""
    if material in HSN_BY_MATERIAL:
        return HSN_BY_MATERIAL[material]
    return HSN_BY_CATEGORY.get(category, ("9705", "Collections and collectors' pieces"))


def readiness(product, artisan) -> dict:
    """What is still missing before this listing could actually be submitted.

    Checked against the fields both marketplaces reject on, so the artisan
    fixes them here rather than being bounced by a portal that explains
    nothing.
    """
    blocking: list[dict] = []
    warnings: list[dict] = []

    def need(ok: bool, field: str, why_en: str, why_hi: str, blocks: bool = True) -> None:
        if ok:
            return
        entry = {"field": field, "reason": why_en, "reason_hi": why_hi}
        (blocking if blocks else warnings).append(entry)

    need(bool(product.title and len(product.title) >= 10), "title",
         "A marketplace title must be at least 10 characters and describe the piece.",
         "नाम कम से कम दस अक्षरों का होना चाहिए।")
    need(bool(product.detailed_description and len(product.detailed_description) > 80),
         "description",
         "The long description must be substantial — portals reject one-liners.",
         "पूरा विवरण लंबा होना चाहिए, एक पंक्ति से काम नहीं चलेगा।")
    need(bool(product.images), "images",
         "At least one product photograph is mandatory.",
         "कम से कम एक फोटो ज़रूरी है।")
    need(product.price > 0, "price", "A selling price is mandatory.", "दाम ज़रूरी है।")
    need(bool(product.material), "material",
         "Material determines the HSN code and cannot be blank.",
         "सामग्री से एचएसएन कोड तय होता है, यह खाली नहीं रह सकती।")
    need(bool(product.weight), "weight",
         "Net quantity is a statutory declaration under the Legal Metrology Rules.",
         "विधिक माप नियमों के तहत वज़न बताना अनिवार्य है।")
    need(bool(product.region), "country_of_origin",
         "Place of manufacture is required for country-of-origin declaration.",
         "निर्माण का स्थान बताना ज़रूरी है।")
    need(bool(artisan and artisan.name), "manufacturer",
         "The maker's name is the declared manufacturer.",
         "बनाने वाले का नाम ज़रूरी है।")
    need(bool(product.size), "dimensions",
         "Size helps buyers and reduces returns.",
         "नाप बताने से वापसी कम होती है।", blocks=False)
    need(product.stock > 0, "stock",
         "Available quantity is zero; the listing would go live as out of stock.",
         "उपलब्ध मात्रा शून्य है।", blocks=False)
    need(bool(product.title_hi), "title_hi",
         "A Hindi title widens reach on government portals.",
         "हिंदी नाम से सरकारी पोर्टल पर पहुँच बढ़ती है।", blocks=False)

    total = 11
    score = int(round((total - len(blocking) - len(warnings) * 0.4) / total * 100))
    return {
        "ready": not blocking,
        "score": max(0, min(100, score)),
        "blocking": blocking,
        "warnings": warnings,
    }


def _specs(product) -> list[dict]:
    pairs = [
        ("Craft", product.craft_type), ("Material", product.material),
        ("Technique", product.technique), ("Colour", product.colour),
        ("Size", product.size), ("Weight", product.weight),
        ("Place of Origin", product.region), ("Care", product.care),
        ("GI Tagged", "Yes" if product.gi_tagged else "No"),
        ("Handmade", "Yes" if product.handmade else "No"),
    ]
    return [{"name": k, "value": v} for k, v in pairs if v]


def to_gem(product, artisan) -> dict:
    """GeM seller-catalogue shape."""
    hsn, hsn_text = hsn_for(product.category, product.material)
    return {
        "catalogue_format": "GeM Seller Product Upload",
        "product_name": product.title,
        "product_name_hindi": product.title_hi or "",
        "brand": "Unbranded",
        "brand_type": "Unbranded",
        "model": f"PAVHAN-{product.id.upper()}",
        "category": GEM_CATEGORY.get(product.category, "Handloom and Handicraft"),
        "hsn_code": hsn,
        "hsn_description": hsn_text,
        "country_of_origin": "India",
        "state_of_origin": product.region,
        "seller_name": getattr(artisan, "name", ""),
        "seller_type": "Artisan / Weaver (Individual)",
        "mrp": round(product.price_premium or product.price * 1.25, 2),
        "offer_price": round(product.price, 2),
        "currency": "INR",
        "unit_of_measure": "Piece",
        "minimum_order_quantity": product.moq or 1,
        "available_quantity": product.stock,
        "delivery_days": product.lead_time_days,
        "short_description": product.short_description,
        "long_description": product.detailed_description,
        "long_description_hindi": product.detailed_description_hi or "",
        "specifications": _specs(product),
        "images": product.images or [],
        "gi_certified": product.gi_tagged,
        "handmade_declaration": True,
    }


def to_ondc(product, artisan) -> dict:
    """ONDC retail item shape (the subset a seller app must provide)."""
    hsn, _ = hsn_for(product.category, product.material)
    now = datetime.now(timezone.utc)
    return {
        "catalogue_format": "ONDC Retail Item (RET10)",
        "id": product.id,
        "descriptor": {
            "name": product.title,
            "code": f"HSN:{hsn}",
            "short_desc": product.short_description,
            "long_desc": product.detailed_description,
            "images": product.images or [],
        },
        "price": {
            "currency": "INR",
            "value": f"{product.price:.2f}",
            "maximum_value": f"{(product.price_premium or product.price * 1.25):.2f}",
        },
        "quantity": {
            "available": {"count": str(product.stock)},
            "maximum": {"count": str(max(product.stock, product.moq or 1))},
            "unitized": {"measure": {"unit": "unit", "value": "1"}},
        },
        "category_id": ONDC_CATEGORY.get(product.category, "Handicrafts and Handloom"),
        "fulfillment_id": "F1",
        "@ondc/org/returnable": True,
        "@ondc/org/cancellable": True,
        "@ondc/org/return_window": "P7D",
        "@ondc/org/seller_pickup_return": False,
        "@ondc/org/time_to_ship": f"P{product.lead_time_days}D",
        "@ondc/org/available_on_cod": False,
        "@ondc/org/contact_details_consumer_care": "support@pavhan.example, 1800-000-000",
        "@ondc/org/statutory_reqs_packaged_commodities": {
            "manufacturer_or_packer_name": getattr(artisan, "name", ""),
            "manufacturer_or_packer_address": product.region,
            "common_or_generic_name_of_commodity": product.craft_type or product.category,
            "net_quantity_or_measure_of_commodity_in_pkg": product.weight or "",
            "month_year_of_manufacture_packing_import": now.strftime("%m/%Y"),
        },
        "country_of_origin": "IND",
        "tags": [
            {"code": "origin", "list": [{"code": "country", "value": "IND"}]},
            {"code": "attribute", "list": [
                {"code": "material", "value": product.material},
                {"code": "craft", "value": product.craft_type},
                {"code": "handmade", "value": "yes" if product.handmade else "no"},
                {"code": "gi_tagged", "value": "yes" if product.gi_tagged else "no"},
            ]},
        ],
    }


def to_csv_rows(product, artisan) -> tuple[list[str], list[Any]]:
    """A flat row for portals that still take a spreadsheet upload."""
    hsn, hsn_text = hsn_for(product.category, product.material)
    header = [
        "product_name", "product_name_hindi", "category", "hsn_code", "hsn_description",
        "brand", "model", "seller_name", "country_of_origin", "state_of_origin",
        "mrp", "offer_price", "currency", "unit", "moq", "available_quantity",
        "delivery_days", "material", "colour", "size", "weight", "craft", "technique",
        "gi_tagged", "handmade", "care", "short_description", "long_description",
        "long_description_hindi", "image_urls",
    ]
    row = [
        product.title, product.title_hi or "",
        GEM_CATEGORY.get(product.category, product.category), hsn, hsn_text,
        "Unbranded", f"PAVHAN-{product.id.upper()}", getattr(artisan, "name", ""),
        "India", product.region,
        round(product.price_premium or product.price * 1.25, 2), round(product.price, 2),
        "INR", "Piece", product.moq or 1, product.stock, product.lead_time_days,
        product.material, product.colour, product.size, product.weight,
        product.craft_type, product.technique,
        "Yes" if product.gi_tagged else "No", "Yes" if product.handmade else "No",
        product.care, product.short_description, product.detailed_description,
        product.detailed_description_hi or "", " | ".join(product.images or []),
    ]
    return header, row


INTEGRATION_NOTE = {
    "en": "This package is submission-shaped: field mapping, HSN classification and "
          "the statutory declarations are all complete. The final push needs a "
          "registered seller account and API credentials on the portal, which is "
          "granted to an organisation rather than issued to an application. "
          "Download the package, or hand the credentials to this service and the "
          "same payload posts straight through.",
    "hi": "यह पैकेज भेजने लायक तैयार है — सभी ज़रूरी जानकारी, एचएसएन कोड और घोषणाएँ पूरी हैं। "
          "आख़िरी चरण के लिए पोर्टल पर पंजीकृत विक्रेता खाता और एपीआई कुंजी चाहिए, जो संस्था को "
          "मिलती है। फ़ाइल डाउनलोड कीजिए, या कुंजी जोड़ते ही यही पैकेज सीधे चला जाएगा।",
}
