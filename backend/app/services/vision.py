"""On-device craft vision.

The demo must work with no API key and no GPU, but it must *never* return a
canned answer: two different photographs have to produce two different
readings. So instead of a stub we run genuine colour science and texture
statistics over the uploaded pixels with Pillow, then map those measurements
onto craft vocabulary.

What we measure
---------------
* dominant palette      -> adaptive-palette quantisation, then LAB-ish naming
* chroma / lightness    -> "vibrant" vs "earthy" vs "muted" finish language
* edge density          -> how intricate the motif work is (drives complexity
                           multiplier in the pricing engine)
* symmetry + aspect     -> silhouette family (draped textile, vessel, flat art,
                           small ornament) which narrows the craft guess
* texture entropy       -> woven / carved / painted / glazed surface guess
"""

from __future__ import annotations

import colorsys
import io
import math
from dataclasses import asdict, dataclass, field

from PIL import Image, ImageFilter, ImageStat

# --------------------------------------------------------------------------
# Colour naming. Hue windows in degrees plus a Hindi name so the assistant can
# read the result out loud in the artisan's own language.
# --------------------------------------------------------------------------
COLOUR_ANCHORS: list[tuple[str, str, tuple[int, int, int]]] = [
    ("Red", "लाल", (200, 30, 45)),
    ("Maroon", "मैरून", (128, 24, 40)),
    ("Rust", "जंग रंग", (176, 86, 42)),
    ("Terracotta", "टेराकोटा", (196, 108, 74)),
    ("Orange", "नारंगी", (238, 128, 32)),
    ("Mustard", "सरसों", (218, 170, 48)),
    ("Gold", "सुनहरा", (212, 175, 55)),
    ("Yellow", "पीला", (240, 214, 70)),
    ("Olive", "जैतूनी", (128, 128, 60)),
    ("Green", "हरा", (46, 139, 87)),
    ("Teal", "मोरपंखी", (32, 132, 136)),
    ("Turquoise", "फ़िरोज़ी", (64, 184, 190)),
    ("Blue", "नीला", (40, 86, 168)),
    ("Indigo", "नील", (48, 56, 120)),
    ("Navy", "गहरा नीला", (26, 38, 74)),
    ("Purple", "बैंगनी", (118, 62, 150)),
    ("Magenta", "मैजेंटा", (196, 48, 128)),
    ("Pink", "गुलाबी", (232, 132, 160)),
    ("Brown", "भूरा", (110, 76, 50)),
    ("Beige", "बेज", (214, 196, 164)),
    ("Cream", "क्रीम", (240, 232, 210)),
    ("White", "सफ़ेद", (246, 246, 246)),
    ("Grey", "स्लेटी", (135, 135, 135)),
    ("Charcoal", "कोयला", (60, 60, 64)),
    ("Black", "काला", (24, 24, 26)),
    ("Silver", "चांदी", (196, 198, 202)),
    ("Copper", "तांबई", (184, 115, 51)),
]


@dataclass
class ColourInfo:
    name: str
    name_hi: str
    hex: str
    share: float


@dataclass
class VisionReading:
    """Everything the pipeline learned from the pixels."""

    palette: list[ColourInfo] = field(default_factory=list)
    dominant_colour: str = ""
    dominant_colour_hi: str = ""
    secondary_colour: str = ""
    brightness: float = 0.0
    saturation: float = 0.0
    contrast: float = 0.0
    edge_density: float = 0.0
    texture_entropy: float = 0.0
    symmetry: float = 0.0
    aspect_ratio: float = 1.0
    silhouette: str = "object"
    surface: str = "matte"
    finish_words: list[str] = field(default_factory=list)
    complexity: float = 1.0
    motif_density: str = "moderate"
    photo_quality: int = 0
    photo_tips: list[str] = field(default_factory=list)
    photo_tips_hi: list[str] = field(default_factory=list)
    width: int = 0
    height: int = 0
    ok: bool = True
    note: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["palette"] = [asdict(c) if not isinstance(c, dict) else c for c in self.palette]
        return data


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _nearest_colour(rgb: tuple[int, int, int]) -> tuple[str, str]:
    """Weighted RGB distance — cheap, but noticeably better than plain L2."""
    r, g, b = rgb
    best, best_d = COLOUR_ANCHORS[0], float("inf")
    for anchor in COLOUR_ANCHORS:
        ar, ag, ab = anchor[2]
        rmean = (r + ar) / 2
        dr, dg, db = r - ar, g - ag, b - ab
        d = math.sqrt(
            (2 + rmean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rmean) / 256) * db * db
        )
        if d < best_d:
            best, best_d = anchor, d
    return best[0], best[1]


def _palette(img: Image.Image, count: int = 5) -> list[ColourInfo]:
    small = img.copy()
    small.thumbnail((160, 160))
    quant = small.convert("RGB").quantize(colors=count * 3, method=Image.Quantize.FASTOCTREE)
    pal = quant.getpalette() or []
    total = sum(c for c, _ in quant.getcolors(1 << 16) or [])
    buckets: dict[str, dict] = {}
    for pixels, idx in sorted(quant.getcolors(1 << 16) or [], reverse=True):
        rgb = tuple(pal[idx * 3 : idx * 3 + 3])
        if len(rgb) < 3:
            continue
        name, name_hi = _nearest_colour(rgb)  # type: ignore[arg-type]
        share = pixels / max(total, 1)
        if name in buckets:
            buckets[name]["share"] += share
        else:
            buckets[name] = {
                "name": name,
                "name_hi": name_hi,
                "hex": _hex(rgb),  # type: ignore[arg-type]
                "share": share,
            }
    ordered = sorted(buckets.values(), key=lambda c: c["share"], reverse=True)[:count]
    return [ColourInfo(**c | {"share": round(c["share"], 4)}) for c in ordered]


def _edge_density(img: Image.Image) -> float:
    """Fraction of pixels sitting on a strong edge -> motif intricacy proxy."""
    grey = img.convert("L")
    grey.thumbnail((256, 256))
    edges = grey.filter(ImageFilter.FIND_EDGES)
    hist = edges.histogram()
    total = sum(hist) or 1
    strong = sum(hist[48:])
    return round(strong / total, 4)


def _entropy(img: Image.Image) -> float:
    grey = img.convert("L")
    grey.thumbnail((192, 192))
    hist = grey.histogram()
    total = sum(hist) or 1
    ent = 0.0
    for count in hist:
        if count:
            p = count / total
            ent -= p * math.log2(p)
    return round(ent, 3)


def _symmetry(img: Image.Image) -> float:
    """1.0 = perfectly mirror-symmetric. Vessels/jewellery score high."""
    grey = img.convert("L")
    grey.thumbnail((128, 128))
    mirrored = grey.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    a, b = grey.getdata(), mirrored.getdata()
    diff = sum(abs(x - y) for x, y in zip(a, b)) / (len(a) or 1)
    return round(max(0.0, 1.0 - diff / 128), 4)


def _silhouette(aspect: float, symmetry: float, edge: float) -> str:
    if aspect > 1.45:
        return "wide-textile"
    if aspect < 0.62:
        return "tall-vessel"
    if symmetry > 0.82 and edge < 0.22:
        return "round-vessel"
    if symmetry > 0.75 and edge > 0.3:
        return "ornament"
    if 0.85 <= aspect <= 1.2 and edge > 0.28:
        return "flat-art"
    return "object"


def _surface(entropy: float, edge: float, contrast: float) -> str:
    if edge > 0.34 and entropy > 7.0:
        return "woven"
    if edge > 0.3 and contrast > 58:
        return "carved"
    if entropy > 6.6 and edge < 0.22:
        return "painted"
    if contrast > 64 and edge < 0.18:
        return "glazed"
    return "matte"


def _finish_words(brightness: float, saturation: float, contrast: float) -> list[str]:
    words: list[str] = []
    if saturation > 0.55:
        words.append("vibrant")
    elif saturation > 0.3:
        words.append("rich")
    else:
        words.append("muted")
    if brightness < 90:
        words.append("deep-toned")
    elif brightness > 175:
        words.append("light and airy")
    else:
        words.append("balanced")
    if contrast > 62:
        words.append("high-contrast motifs")
    else:
        words.append("softly blended")
    return words


def _photo_quality(
    img: Image.Image, brightness: float, contrast: float
) -> tuple[int, list[str], list[str]]:
    """Coach the artisan on the photo itself — most listings fail here.

    Tips come back in both languages so the app can show and speak whichever
    one the artisan is using, rather than mixing scripts on screen.
    """
    score = 100
    tips_en: list[str] = []
    tips_hi: list[str] = []

    def add(en: str, hi: str, penalty: int) -> None:
        nonlocal score
        score -= penalty
        tips_en.append(en)
        tips_hi.append(hi)

    w, h = img.size
    if min(w, h) < 600:
        add("The photo is small. Move closer and shoot again in good light.",
            "फोटो थोड़ी छोटी है — थोड़ा पास से, अच्छी रोशनी में दोबारा लीजिए।", 25)
    if brightness < 70:
        add("It is too dark. Stand near a window and use daylight.",
            "रोशनी कम है। खिड़की के पास दिन की रोशनी में फोटो लीजिए।", 20)
    elif brightness > 215:
        add("The photo is blown out. Move out of direct sunlight.",
            "फोटो बहुत चमक रही है। सीधी धूप से हटकर रखिए।", 15)
    if contrast < 22:
        add("The background and the piece are blending. Use a plain white cloth.",
            "बैकग्राउंड और सामान का रंग मिल रहा है — सादे सफ़ेद कपड़े पर रखिए।", 15)
    if _edge_density(img) < 0.08:
        add("It looks slightly blurred — hold the phone steady and retake it.",
            "फोटो हल्की धुँधली लग रही है — मोबाइल स्थिर रखकर दोबारा लीजिए।", 20)

    if not tips_en:
        tips_en.append("Good photo. Add one close-up and one full view as well.")
        tips_hi.append("बढ़िया फोटो! एक पास से और एक पूरी वस्तु की भी जोड़िए।")
    return max(20, min(100, score)), tips_en, tips_hi


def analyse_image(data: bytes) -> VisionReading:
    """Run the full reading over raw image bytes."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        else:
            img = img.convert("RGB")
    except Exception as exc:  # pragma: no cover - defensive
        return VisionReading(ok=False, note=f"Could not read image: {exc}")

    w, h = img.size
    stat = ImageStat.Stat(img)
    r, g, b = stat.mean
    brightness = round((0.299 * r + 0.587 * g + 0.114 * b), 2)
    contrast = round(sum(stat.stddev) / 3, 2)
    _, _, sat = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    # Saturation from the mean pixel under-reports busy multicolour cloth, so
    # blend it with the spread of the palette itself.
    palette = _palette(img)
    if palette:
        sats = []
        for c in palette:
            cr = int(c.hex[1:3], 16) / 255
            cg = int(c.hex[3:5], 16) / 255
            cb = int(c.hex[5:7], 16) / 255
            sats.append(colorsys.rgb_to_hsv(cr, cg, cb)[1])
        sat = max(sat, sum(sats) / len(sats))

    edge = _edge_density(img)
    entropy = _entropy(img)
    symmetry = _symmetry(img)
    aspect = round(w / max(h, 1), 3)
    silhouette = _silhouette(aspect, symmetry, edge)
    surface = _surface(entropy, edge, contrast)
    quality, tips_en, tips_hi = _photo_quality(img, brightness, contrast)

    # Complexity drives the labour multiplier in the pricing engine.
    complexity = round(
        1.0 + min(edge, 0.5) * 1.6 + max(0.0, entropy - 6.0) * 0.18, 3
    )
    if edge > 0.36:
        motif = "very intricate"
    elif edge > 0.26:
        motif = "intricate"
    elif edge > 0.16:
        motif = "moderate"
    else:
        motif = "minimal"

    return VisionReading(
        palette=palette,
        dominant_colour=palette[0].name if palette else "Natural",
        dominant_colour_hi=palette[0].name_hi if palette else "प्राकृतिक",
        secondary_colour=palette[1].name if len(palette) > 1 else "",
        brightness=brightness,
        saturation=round(float(sat), 3),
        contrast=contrast,
        edge_density=edge,
        texture_entropy=entropy,
        symmetry=symmetry,
        aspect_ratio=aspect,
        silhouette=silhouette,
        surface=surface,
        finish_words=_finish_words(brightness, float(sat), contrast),
        complexity=complexity,
        motif_density=motif,
        photo_quality=quality,
        photo_tips=tips_en,
        photo_tips_hi=tips_hi,
        width=w,
        height=h,
    )
