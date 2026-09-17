"""Listing generation: photo + voice -> a catalogue entry.

The failure this module exists to fix: the old prototype returned the same
Banarasi saree no matter what was uploaded. Here the craft is *inferred* by
combining three independent evidence streams and the result changes whenever
any of them changes:

    keyword evidence from the transcript   (weight 0.60)
    colour-palette affinity from the photo (weight 0.22)
    silhouette + surface from the photo    (weight 0.18)

If the combined evidence is too weak we say so and ask the artisan a question
rather than guessing confidently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import nlp
from .taxonomy import CRAFTS, CRAFT_INDEX, LANGUAGE_AFFINITY, Craft
from .vision import VisionReading


@dataclass
class CraftGuess:
    craft: Craft
    confidence: int
    evidence: list[str] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)


def infer_craft(facts: nlp.TranscriptFacts, vision: VisionReading | None) -> CraftGuess:
    scores: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}
    # The language an artisan speaks is itself evidence about which cluster
    # they work in — "silk saree" in Tamil means Kanjeevaram, not Banarasi.
    affinity = set(LANGUAGE_AFFINITY.get(facts.language, []))

    for craft in CRAFTS:
        text_score = facts.craft_scores.get(craft.key, 0.0)
        colour_score = 0.0
        shape_score = 0.0
        why: list[str] = []

        if text_score:
            why.append(f"you said words specific to {craft.name}")

        if vision and vision.ok and vision.palette:
            names = [c.name for c in vision.palette[:3]]
            overlap = len(set(names) & set(craft.colour_affinity))
            colour_score = min(1.0, overlap / 2.0)
            if overlap:
                why.append(f"the photo's {', '.join(names[:2])} palette matches this craft")
            if vision.silhouette in craft.silhouettes:
                shape_score += 0.6
                why.append(f"the shape reads as a {vision.silhouette.replace('-', ' ')}")
            if vision.surface in craft.surfaces:
                shape_score += 0.4
                why.append(f"the surface looks {vision.surface}")

        # Material stated by the artisan is strong corroboration.
        material_bonus = 0.0
        for m in facts.materials:
            if m.lower() in craft.default_material.lower() or craft.default_material.lower() in m.lower():
                material_bonus = 0.35
                why.append(f"you named {m}, the material this craft uses")
                break
        region_bonus = 0.0
        for r in facts.regions:
            if any(r.lower() in cr.lower() or cr.lower() in r.lower() for cr in craft.regions):
                region_bonus = 0.3
                why.append(f"{r} is a home cluster for this craft")
                break

        language_bonus = 0.0
        if craft.key in affinity:
            language_bonus = 0.28
            why.append(f"you spoke in a language of this craft's home region")

        total = (
            text_score * 0.60
            + colour_score * 0.22
            + min(shape_score, 1.0) * 0.18
            + material_bonus
            + region_bonus
            + language_bonus
        )
        if total > 0:
            scores[craft.key] = round(total, 4)
            evidence[craft.key] = why

    if not scores:
        # Nothing matched. Fall back on silhouette alone rather than a hardcoded craft.
        fallback = "terracotta"
        if vision and vision.ok:
            by_shape = [c for c in CRAFTS if vision.silhouette in c.silhouettes]
            if by_shape:
                fallback = by_shape[0].key
        return CraftGuess(
            craft=CRAFT_INDEX[fallback],
            confidence=22,
            evidence=["We could not identify the craft with confidence — please confirm it below."],
            alternatives=[],
        )

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_key, top_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    # Confidence rewards both absolute evidence and separation from second place.
    separation = (top_score - runner_up) / max(top_score, 0.01)
    confidence = int(min(96, 34 + top_score * 46 + separation * 22))

    return CraftGuess(
        craft=CRAFT_INDEX[top_key],
        confidence=confidence,
        evidence=evidence.get(top_key, [])[:4],
        alternatives=[
            {"key": k, "name": CRAFT_INDEX[k].name, "score": round(v / max(top_score, 0.01), 3)}
            for k, v in ranked[1:4]
        ],
    )


def _title(craft: Craft, facts: nlp.TranscriptFacts, vision: VisionReading | None) -> str:
    noun = facts.product_noun or _noun_from_shape(craft, vision)
    colour = facts.colours[0] if facts.colours else (
        vision.dominant_colour if vision and vision.ok else ""
    )
    technique = facts.techniques[0] if facts.techniques else ""
    bits = [b for b in (colour, technique) if b and b.lower() != "handmade"]
    core = craft.name.replace(" Craft", "").replace(" Painting", "")
    parts = [*bits, core, noun]
    # "Blue Jaipur Blue Pottery Bowl" reads like a bug, so drop any word the
    # title already carries, keeping the first occurrence.
    seen: set[str] = set()
    words: list[str] = []
    for part in parts:
        for word in str(part).split():
            key = word.lower().strip("-,")
            if key and key not in seen:
                seen.add(key)
                words.append(word)
    return " ".join(words)[:70]


def _noun_from_shape(craft: Craft, vision: VisionReading | None) -> str:
    if not vision or not vision.ok:
        return craft.unit.title()
    return {
        "wide-textile": "Drape", "tall-vessel": "Vase", "round-vessel": "Bowl",
        "flat-art": "Wall Art", "ornament": "Piece",
    }.get(vision.silhouette, craft.unit.title())


def _short_description(craft: Craft, facts: nlp.TranscriptFacts, vision: VisionReading | None) -> str:
    colour = facts.colours[0] if facts.colours else (
        vision.dominant_colour if vision and vision.ok else "natural"
    )
    finish = vision.finish_words[0] if vision and vision.ok and vision.finish_words else "handmade"
    region = facts.regions[0] if facts.regions else (craft.regions[0] if craft.regions else "India")
    return (
        f"A {finish} {colour.lower()} {craft.name.lower()} piece, made entirely by hand "
        f"in {region}."
    )[:200]


def _detailed_description(
    craft: Craft, facts: nlp.TranscriptFacts, vision: VisionReading | None
) -> str:
    region = facts.regions[0] if facts.regions else (craft.regions[0] if craft.regions else "India")
    lines = [
        f"This is a {craft.name.lower()} piece made in {region} using "
        f"{(facts.techniques[0] if facts.techniques else 'traditional hand')} technique."
    ]
    if vision and vision.ok:
        colours = ", ".join(c.name.lower() for c in vision.palette[:3])
        lines.append(
            f"The piece reads {', '.join(vision.finish_words)}, working in {colours}, "
            f"with {vision.motif_density} motif work across the surface."
        )
    details = []
    if facts.materials:
        details.append(f"made from {facts.materials[0].lower()}")
    if facts.size:
        details.append(f"measuring {facts.size}")
    if facts.weight:
        details.append(f"weighing {facts.weight}")
    if details:
        lines.append("It is " + ", ".join(details) + ".")
    if facts.making_days:
        lines.append(
            f"The artisan spent {facts.making_days:g} day"
            f"{'s' if facts.making_days != 1 else ''} making this single piece."
        )
    elif facts.making_hours:
        lines.append(f"The artisan spent {facts.making_hours:g} hours on this single piece.")
    if facts.mentions_natural_dye:
        lines.append("Only natural, chemical-free dyes were used.")
    lines.append(
        "Because it is made by hand, small variations in the motif are part of the piece "
        "and not a defect."
    )
    return " ".join(lines)


# ---------------------------------------------------------------------------
# Hindi copy.
#
# The problem statement asks for professional descriptions in English AND
# Hindi. With no Claude key the engine previously wrote English only, so the
# Hindi fields came back empty. These generators mirror the English ones
# exactly — same facts, same structure, nothing invented — but compose Hindi
# sentences rather than translating word by word, because a literal
# translation of English marketing copy reads like a form, not like a person.
# ---------------------------------------------------------------------------
# Anything that still has a Latin letter in it after all the lookups. Used as
# the last line of defence in every Hindi builder below.
LATIN = re.compile(r"[A-Za-z]")


def _hi(value: str, table: dict[str, str]) -> str:
    """Hindi name for a data token, falling back to the token itself."""
    return table.get(value, value)


UNITS_HI = {
    "metre": "मीटर", "meter": "मीटर", "gram": "ग्राम", "kg": "किलो",
    "inch": "इंच", "feet": "फुट", "foot": "फुट", "cm": "सेंटीमीटर",
    "mm": "मिलीमीटर", "ml": "मिलीलीटर", "litre": "लीटर", "x": "×",
    # A measurement is rarely just a number and a unit. The catalogue carries
    # "9 inch tall", "22 cm each", "4 cm drop", "42 inch chest" — and a
    # qualifier with no entry here survives untranslated into the middle of a
    # Hindi sentence, which is exactly what "the Hindi description is mixed"
    # looks like from the artisan's side.
    "tall": "ऊँचा", "wide": "चौड़ा", "long": "लंबा", "high": "ऊँचा",
    "deep": "गहरा", "each": "प्रत्येक", "drop": "लटकन", "chest": "छाती",
    "diameter": "व्यास", "square": "वर्ग", "round": "गोल", "set": "जोड़ा",
    "approx": "लगभग", "per piece": "प्रति नग", "pair": "जोड़ी",
}


def _measure_hi(value: str | None) -> str:
    """"5.5 metre tall" -> "5.5 मीटर ऊँचा". Numbers stay, words become Hindi.

    Longest keys first, so "per piece" is matched before "piece" would be.
    Anything still in Latin script after the pass is dropped rather than
    shown — a measurement missing its qualifier still reads as Hindi; one
    English word inside it does not.
    """
    if not value:
        return ""
    out = value
    for english in sorted(UNITS_HI, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(english)}\b", UNITS_HI[english], out,
                     flags=re.IGNORECASE)
    kept = [tok for tok in out.split() if not LATIN.search(tok)]
    return " ".join(kept)


# A craft's `unit` is an English word ("painting", "figurine", "piece"), and
# it is the fallback when an artisan's own noun is not recognised. Dropped
# straight into a Hindi title it produced "पीला मधुबनी चित्रकला painting" —
# the mixed-script output that made the Hindi listing look broken.
UNIT_HI = {
    "piece": "कृति", "saree": "साड़ी", "shawl": "शॉल", "dupatta": "दुपट्टा",
    "painting": "चित्र", "figurine": "प्रतिमा", "toy": "खिलौना",
    "garment": "परिधान", "panel": "फलक", "mekhela chador": "मेखला चादर",
    "stole": "स्टोल", "scarf": "स्कार्फ़", "rug": "दरी", "carpet": "कालीन",
}

NOUN_HI = {
    "Saree": "साड़ी", "Dupatta": "दुपट्टा", "Stole": "स्टोल", "Scarf": "स्कार्फ़",
    "Shawl": "शॉल", "Kurta": "कुर्ता", "Kurti": "कुर्ती", "Suit Set": "सूट",
    "Painting": "चित्र", "Artwork": "कलाकृति", "Vase": "गुलदस्ता", "Pot": "मटका",
    "Bowl": "कटोरी", "Plate": "थाली", "Diya": "दीया", "Lamp": "दीपक",
    "Toy": "खिलौना", "Basket": "टोकरी", "Bag": "थैला", "Earrings": "बालियाँ",
    "Jhumka": "झुमका", "Necklace": "हार", "Bangles": "चूड़ियाँ", "Idol": "मूर्ति",
    "Figurine": "प्रतिमा", "Quilt": "रज़ाई", "Throw": "चादर",
    "Cushion Cover": "कुशन कवर", "Table Runner": "टेबल रनर", "Rug": "दरी",
    "Carpet": "कालीन", "Storage Box": "डिब्बा", "Mask": "मुखौटा",
    "Wall Hanging": "दीवार सज्जा", "Panel": "फलक", "Tray": "थाली",
    "Rattle": "झुनझुना",
    # Deliberately no "Set" or "Horse": they are modifiers, and matching them
    # first turned "Dinner Plate Set" into "जोड़ा" when it should find "Plate".
}

def _noun_hi(noun: str | None, craft: Craft) -> str:
    """The Hindi word for whatever the artisan called their piece.

    An exact lookup is not enough, because a real noun is rarely a bare
    dictionary word: the catalogue carries "Wall Painting", "Dinner Plate
    Set", "Meenakari Jhumka", "Tribal Horse Figurine". So this tries the whole
    phrase, then its last word, then any known noun appearing anywhere in it —
    longest first, so "Storage Box" is not matched as "Box" when both would
    do.

    When nothing matches it falls back to the craft's unit in Hindi, and if
    even that is unknown it returns empty. Returning an English word here is
    the one thing it must never do.
    """
    if noun:
        cleaned = noun.strip()
        if cleaned in NOUN_HI:
            return NOUN_HI[cleaned]
        last = cleaned.split()[-1] if cleaned.split() else ""
        if last in NOUN_HI:
            return NOUN_HI[last]
        lowered = cleaned.lower()
        for key in sorted(NOUN_HI, key=len, reverse=True):
            if key.lower() in lowered:
                return NOUN_HI[key]
    return UNIT_HI.get((craft.unit or "").lower(), "")


def _title_hi(craft: Craft, facts: nlp.TranscriptFacts, vision: VisionReading | None) -> str:
    from .taxonomy import colour_labels

    colours = colour_labels()
    noun = _noun_hi(facts.product_noun, craft)
    colour = facts.colours[0] if facts.colours else (
        vision.dominant_colour if vision and vision.ok else ""
    )
    colour_word = _hi(colour, colours) if colour else ""
    # Any part that is still Latin script is dropped rather than shown. A
    # slightly shorter Hindi title reads as Hindi; one English word in the
    # middle of it reads as a bug, and to the artisan it reads as the app not
    # really speaking their language.
    parts = [p for p in (colour_word, craft.name_hi, noun) if p and not LATIN.search(p)]
    return " ".join(dict.fromkeys(parts))[:70]


def _short_description_hi(craft: Craft, facts: nlp.TranscriptFacts, vision: VisionReading | None) -> str:
    from .taxonomy import REGION_HI, colour_labels

    colour = facts.colours[0] if facts.colours else (
        vision.dominant_colour if vision and vision.ok else ""
    )
    colour_word = _hi(colour, colour_labels()) if colour else ""
    region = facts.regions[0] if facts.regions else (craft.regions[0] if craft.regions else "भारत")
    region_hi = _hi(region, REGION_HI)
    colour_part = f"{colour_word} रंग की " if colour_word else ""
    return f"{region_hi} में हाथ से बनी {colour_part}{craft.name_hi} कृति।"[:200]


def _detailed_description_hi(
    craft: Craft, facts: nlp.TranscriptFacts, vision: VisionReading | None
) -> str:
    from .taxonomy import MATERIAL_HI, REGION_HI, TECHNIQUE_HI, colour_labels

    colours = colour_labels()
    region = facts.regions[0] if facts.regions else (craft.regions[0] if craft.regions else "भारत")
    technique = facts.techniques[0] if facts.techniques else ""
    technique_hi = _hi(technique, TECHNIQUE_HI) if technique else "पारंपरिक हस्तकला"

    lines = [
        f"यह {_hi(region, REGION_HI)} की {craft.name_hi} है, जिसे {technique_hi} "
        f"तकनीक से बनाया गया है।"
    ]
    if vision and vision.ok and vision.palette:
        shades = "、".join(_hi(c.name, colours) for c in vision.palette[:3]).replace("、", ", ")
        density = {
            "very intricate": "बहुत बारीक", "intricate": "बारीक",
            "moderate": "संतुलित", "minimal": "सादा",
        }.get(vision.motif_density, "संतुलित")
        lines.append(f"इसमें {shades} रंग हैं और डिज़ाइन का काम {density} है।")

    details = []
    if facts.materials:
        details.append(f"{_hi(facts.materials[0], MATERIAL_HI)} से बनी है")
    if facts.size:
        details.append(f"नाप {_measure_hi(facts.size)} है")
    if facts.weight:
        details.append(f"वज़न {_measure_hi(facts.weight)} है")
    if details:
        lines.append("यह " + ", ".join(details) + "।")

    if facts.making_days:
        lines.append(f"इस एक कृति को बनाने में कारीगर को {facts.making_days:g} दिन लगे।")
    elif facts.making_hours:
        lines.append(f"इस एक कृति को बनाने में कारीगर को {facts.making_hours:g} घंटे लगे।")

    if facts.mentions_natural_dye:
        lines.append("इसमें केवल प्राकृतिक रंगों का प्रयोग हुआ है, कोई रसायन नहीं।")

    lines.append(
        "हाथ से बनी होने के कारण डिज़ाइन में हल्का अंतर आ सकता है — यह इसकी "
        "पहचान है, कोई कमी नहीं।"
    )
    return " ".join(lines)


def _story_hi(craft: Craft) -> str:
    return (
        f"{craft.name_hi} की यह कृति पीढ़ियों से चली आ रही कारीगरी का हिस्सा है। "
        f"इसे बनाने में लगा हर घंटा उस कारीगर का है जिसने इसे बनाया।"
    )


def hindi_listing(
    craft: Craft, *, colour: str = "", region: str = "", noun: str = "",
    size: str = "", weight: str = "", making_days: float | None = None,
) -> dict[str, str]:
    """The Hindi half of a listing, built from facts rather than a transcript.

    The voice flow reaches the builders below through `nlp.TranscriptFacts`,
    which is the right shape when an artisan has just spoken. Anything that
    already *knows* the facts — the seed catalogue, an import, a bulk upload —
    has no transcript to hand and would otherwise have to write its own
    Hindi. That is how the demo catalogue ended up English-only: the seed
    quietly skipped these fields, so an artisan who set the app to Hindi
    browsed sixteen listings in the one language the app exists to spare them.

    So the facts are packed into the same structure and the same builders run.
    One set of Hindi, one place to improve it.
    """
    facts = nlp.TranscriptFacts(
        language="hi",
        colours=[colour] if colour else [],
        regions=[region] if region else [],
        product_noun=noun or None,
        size=size or None,
        weight=weight or None,
        making_days=making_days,
    )
    return {
        "title_hi": _title_hi(craft, facts, None),
        "short_description_hi": _short_description_hi(craft, facts, None),
        "detailed_description_hi": _detailed_description_hi(craft, facts, None),
        "story_hi": _story_hi(craft),
        "care_hi": craft.care_hi,
    }


def _tags(craft: Craft, facts: nlp.TranscriptFacts, vision: VisionReading | None) -> list[str]:
    tags = {craft.category.lower(), craft.name.lower(), "handmade", "artisan made"}
    tags.update(t.lower() for t in facts.techniques)
    tags.update(c.lower() for c in facts.colours)
    tags.update(m.lower() for m in facts.materials)
    if facts.regions:
        tags.add(facts.regions[0].lower())
    if craft.gi_tagged:
        tags.add("gi tagged")
    if facts.mentions_natural_dye:
        tags.add("natural dye")
    if vision and vision.ok:
        tags.add(vision.dominant_colour.lower())
        tags.add(vision.surface)
    if facts.product_noun:
        tags.add(facts.product_noun.lower())
    return sorted(t for t in tags if t and len(t) > 2)[:14]


def _quality_score(facts: nlp.TranscriptFacts, vision: VisionReading | None, guess: CraftGuess) -> tuple[int, list[str]]:
    """Honest completeness score — the old app showed 100/100 for everything."""
    score, gaps = 0, []
    if facts.word_count >= 25:
        score += 22
    elif facts.word_count >= 12:
        score += 14
        gaps.append("Describe the piece for a few more seconds — buyers read this.")
    else:
        score += 5
        gaps.append("Your voice note was very short. Say what it is, what it is made of, and how long it took.")

    for label, present, points, tip in (
        ("material", bool(facts.materials), 12, "Say what material it is made of."),
        ("colour", bool(facts.colours), 8, "Name the main colour."),
        ("size", bool(facts.size), 12, "Give the size — buyers filter by it."),
        ("weight", bool(facts.weight), 8, "Mention the weight for shipping."),
        ("making time", facts.making_days is not None or facts.making_hours is not None, 14,
         "Say how long it took — this is what sets your price."),
        ("origin", bool(facts.regions), 10, "Name your town or district."),
        ("care", bool(facts.care), 6, "Tell buyers how to care for it."),
    ):
        if present:
            score += points
        else:
            gaps.append(tip)

    if vision and vision.ok:
        score += int(vision.photo_quality * 0.08)
        if vision.photo_quality < 70:
            gaps.extend(vision.photo_tips[:1])
    else:
        gaps.append("Add a photograph — listings with photos sell 4x more often.")

    if guess.confidence < 55:
        gaps.append("Confirm the craft type below so buyers can find you in search.")

    return max(5, min(100, score)), gaps[:5]


def build_listing(
    transcript: str,
    vision: VisionReading | None = None,
    *,
    language: str = "hi",
) -> dict:
    """The deterministic on-device generator. Always produces a result."""
    # `language` is what the artisan picked in the app; it settles cases the
    # script cannot, such as Marathi versus Hindi in a short Devanagari phrase.
    facts = nlp.extract(transcript, hint=language)
    guess = infer_craft(facts, vision)
    craft = guess.craft

    quality, gaps = _quality_score(facts, vision, guess)
    colour = facts.colours[0] if facts.colours else (
        vision.dominant_colour if vision and vision.ok else ""
    )
    colour_hi = vision.dominant_colour_hi if vision and vision.ok else ""
    region = facts.regions[0] if facts.regions else (craft.regions[0] if craft.regions else "")
    material = facts.materials[0] if facts.materials else craft.default_material
    technique = facts.techniques[0] if facts.techniques else craft.name.split()[0]

    story = (
        f"This piece was {craft.story_hook}. "
        f"Every hour of that work belongs to the artisan who made it."
    )

    listing = {
        "title": _title(craft, facts, vision),
        "short_description": _short_description(craft, facts, vision),
        "detailed_description": _detailed_description(craft, facts, vision),
        "story": story,
        # Hindi copy is generated, not translated — the problem statement asks
        # for professional descriptions in both languages.
        "title_hi": _title_hi(craft, facts, vision),
        "short_description_hi": _short_description_hi(craft, facts, vision),
        "detailed_description_hi": _detailed_description_hi(craft, facts, vision),
        "story_hi": _story_hi(craft),
        "craft_type": craft.name,
        "craft_key": craft.key,
        "category": craft.category,
        "material": material,
        "colour": colour,
        "colour_hi": colour_hi,
        "region": region,
        "technique": technique,
        "size": facts.size or "",
        "weight": facts.weight or craft.typical_weight,
        "care": "; ".join(facts.care) if facts.care else craft.care,
        "care_hi": craft.care_hi,
        "tags": _tags(craft, facts, vision),
        "keywords": craft.seo_terms,
        "gi_tagged": craft.gi_tagged,
        "handmade": True,
        "quality_score": quality,
        "sustainability_score": _sustainability(craft, facts),
        "palette": [c.__dict__ if hasattr(c, "__dict__") else c for c in (vision.palette if vision and vision.ok else [])],
        "language": facts.language or language,
        "spoken_language": facts.language,
        "ai_meta": {
            "engine": "pavhan-on-device-v1",
            "craft_confidence": guess.confidence,
            "craft_evidence": guess.evidence,
            "alternatives": guess.alternatives,
            "transcript_facts": {
                "colours": facts.colours, "materials": facts.materials,
                "techniques": facts.techniques, "regions": facts.regions,
                "size": facts.size, "weight": facts.weight,
                "making_days": facts.making_days, "making_hours": facts.making_hours,
                "expected_price": facts.expected_price,
                "word_count": facts.word_count,
            },
            "vision": vision.to_dict() if vision and vision.ok else None,
            "improvement_tips": gaps,
            "missing_fields": facts.missing_fields,
        },
        "_facts": facts,
        "_craft": craft,
    }
    return listing


def _sustainability(craft: Craft, facts: nlp.TranscriptFacts) -> int:
    score = 55
    natural = {"Bamboo", "Cane", "Jute", "Terracotta Clay", "Cotton", "Khadi",
               "Handmade Paper", "Wood"}
    if craft.default_material in natural or any(m in natural for m in facts.materials):
        score += 20
    if facts.mentions_natural_dye:
        score += 15
    if craft.category == "Natural Fibre":
        score += 10
    if facts.mentions_handmade:
        score += 5
    return min(100, score)


def merge_llm(listing: dict, enriched: dict | None) -> dict:
    """Overlay Claude's copy without letting it overwrite extracted facts."""
    if not enriched:
        return listing
    safe_copy_fields = (
        "title", "short_description", "detailed_description", "story",
        "title_hi", "short_description_hi", "detailed_description_hi", "story_hi",
    )
    for key in safe_copy_fields:
        value = enriched.get(key)
        if isinstance(value, str) and value.strip():
            listing[key] = value.strip()
    if isinstance(enriched.get("tags"), list) and enriched["tags"]:
        listing["tags"] = sorted({*listing["tags"], *[str(t).lower() for t in enriched["tags"]]})[:16]
    if isinstance(enriched.get("seo_keywords"), list) and enriched["seo_keywords"]:
        listing["keywords"] = [str(k) for k in enriched["seo_keywords"]][:12]
    if enriched.get("care_instructions"):
        listing["care"] = str(enriched["care_instructions"])
    if isinstance(enriched.get("suggested_occasions"), list):
        listing["occasions"] = [str(o) for o in enriched["suggested_occasions"]][:4]
    listing["ai_meta"]["engine"] = "claude-enriched"
    if isinstance(enriched.get("confidence"), int):
        listing["ai_meta"]["llm_confidence"] = enriched["confidence"]
    return listing
