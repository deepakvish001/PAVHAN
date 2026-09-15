"""AI Product Studio — turn a phone snapshot into an e-commerce photograph.

This is the feature the problem statement names first, and the one that
decides whether an artisan's listing looks like a marketplace product or a
photo taken on a charpai. Four things go wrong in artisan product photos, and
each has a stage here:

    cluttered background  ->  subject segmentation, then a clean backdrop
    bad light             ->  white balance, exposure lift, local contrast
    soft focus            ->  unsharp masking
    wrong framing         ->  crop to the subject, pad, square, 1600px

Everything runs locally with OpenCV — no model download, no API key, no
network. That matters for a rural-first product and for a demo on venue WiFi.

Segmentation is classical rather than neural, and the report says so: we build
a foreground probability map from a border-colour background model, a centre
prior and an edge map, use it to seed GrabCut, then clean up the mask. On the
plain-ish backgrounds artisans actually shoot against this is reliable; on a
genuinely chaotic background it degrades honestly and tells the artisan to
reshoot against a plain cloth rather than silently mangling the product.
"""

from __future__ import annotations

import io
import math
from dataclasses import asdict, dataclass, field

import numpy as np
from PIL import Image, ImageOps

try:  # pragma: no cover - exercised by the absence test below
    import cv2

    HAS_CV2 = True
except Exception:  # pragma: no cover
    cv2 = None
    HAS_CV2 = False

# E-commerce houses converge on a large square master image.
OUTPUT_SIZE = 1600
WORK_SIZE = 900          # segmentation runs here, then the mask is upscaled
SUBJECT_PADDING = 0.06   # breathing room around the product, as a fraction


@dataclass
class StudioStep:
    """One thing we did, and the measurable reason we did it."""

    key: str
    label: str
    label_hi: str
    applied: bool
    detail: str = ""
    detail_hi: str = ""


@dataclass
class StudioResult:
    ok: bool = True
    note: str = ""
    steps: list[StudioStep] = field(default_factory=list)
    subject_coverage: float = 0.0
    segmentation_confidence: int = 0
    brightness_before: float = 0.0
    brightness_after: float = 0.0
    sharpness_before: float = 0.0
    sharpness_after: float = 0.0
    background_removed: bool = False
    engine: str = "pavhan-studio-cv"
    width: int = 0
    height: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["steps"] = [asdict(s) if not isinstance(s, dict) else s for s in self.steps]
        return data


# ---------------------------------------------------------------------------
# measurements
# ---------------------------------------------------------------------------
def _brightness(rgb: np.ndarray) -> float:
    return float(np.mean(rgb @ np.array([0.299, 0.587, 0.114])))


def _sharpness(rgb: np.ndarray) -> float:
    """Variance of the Laplacian — the standard blur proxy."""
    grey = (rgb @ np.array([0.299, 0.587, 0.114])).astype(np.float32)
    if HAS_CV2:
        return float(cv2.Laplacian(grey, cv2.CV_32F).var())
    gy, gx = np.gradient(grey)
    return float((gx * gx + gy * gy).var())


# ---------------------------------------------------------------------------
# stage 1 — colour correction
# ---------------------------------------------------------------------------
def _subject_pixels(rgb: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
    """The pixels that are actually the product.

    Measuring colour and exposure over the whole frame is what made early
    results look washed out: a photo of a tan basket against a big brown wall
    is mostly wall, so grey-world neutralises the wall *and* drains the basket
    with it. Correct against the product, and the product keeps its colour.
    """
    flat = rgb.reshape(-1, 3)
    if mask is None:
        return flat
    sel = mask.reshape(-1) > 0.5
    return flat[sel] if sel.sum() > 64 else flat


def _white_balance(rgb: np.ndarray, mask: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    """Shades-of-grey white balance, estimated from the product.

    Indoor artisan photos are almost always warm — tungsten bulbs and evening
    light push everything orange, which makes indigo read as grey and silk read
    as muddy.
    """
    img = rgb.astype(np.float32)
    sample = _subject_pixels(rgb, mask).astype(np.float32)
    p = 6.0  # Minkowski norm; 6 behaves better than plain grey-world
    means = np.power(np.mean(np.power(sample + 1e-6, p), axis=0), 1.0 / p)
    grey = float(np.mean(means))
    gains = grey / np.maximum(means, 1e-6)
    # Clamped hard: a craft photo must not be "corrected" into a different
    # colour than the object the buyer will receive.
    gains = np.clip(gains, 0.82, 1.22)
    cast = float(np.max(np.abs(gains - 1.0)))
    out = np.clip(img * gains, 0, 255).astype(np.uint8)
    return out, cast


def _exposure_and_contrast(
    rgb: np.ndarray, mask: np.ndarray | None = None
) -> tuple[np.ndarray, float, bool]:
    """Lift the product to a studio brightness, then add local contrast."""
    sample = _subject_pixels(rgb, mask)
    before = float(np.mean(sample @ np.array([0.299, 0.587, 0.114])))
    target = 158.0                              # where studio product shots sit
    out = rgb

    gamma_applied = False
    if before < 1:
        return rgb, before, False
    ratio = target / before
    if ratio > 1.06 or ratio < 0.94:
        # Gamma rather than a linear scale: it lifts shadows without blowing
        # out the highlights on zari or glaze.
        gamma = float(np.clip(
            math.log(target / 255.0) / math.log(max(before, 1) / 255.0), 0.40, 1.8))
        table = np.clip(np.power(np.arange(256) / 255.0, gamma) * 255.0, 0, 255).astype(np.uint8)
        out = table[out]
        gamma_applied = True

    if HAS_CV2:
        lab = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)
        lightness, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.7, tileGridSize=(8, 8))
        lab = cv2.merge((clahe.apply(lightness), a, b))
        out = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return out, before, gamma_applied


def _saturation(rgb: np.ndarray, factor: float = 1.10) -> np.ndarray:
    """A restrained lift. Craft colours should look like the real object —
    an over-saturated photo is how a buyer ends up disappointed on delivery."""
    if not HAS_CV2:
        return rgb
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * factor, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def _unsharp(rgb: np.ndarray, amount: float = 0.6) -> np.ndarray:
    if not HAS_CV2:
        return rgb
    blur = cv2.GaussianBlur(rgb, (0, 0), 2.2)
    return np.clip(rgb.astype(np.float32) * (1 + amount)
                   - blur.astype(np.float32) * amount, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# stage 2 — subject segmentation
# ---------------------------------------------------------------------------
def _background_clusters(border: np.ndarray, k: int = 3) -> list[tuple]:
    """Model the background as a few colours, not one.

    A single Gaussian over the border fails the moment a photo contains both a
    wall and a floor — the midpoint between them is "far" from the model, so
    the strip of floor under the product survives the cut. Clustering the
    border first gives wall, floor and shadow their own means.
    """
    if not HAS_CV2 or len(border) < k * 8:
        mean = border.mean(axis=0)
        cov = np.cov(border.T) + np.eye(3) * 12.0
        return [(mean, np.linalg.inv(cov))]

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
    _, labels, centres = cv2.kmeans(
        border.astype(np.float32), k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    labels = labels.ravel()

    clusters = []
    for i in range(k):
        members = border[labels == i]
        if len(members) < 12:
            continue
        cov = np.cov(members.T) + np.eye(3) * 14.0
        clusters.append((members.mean(axis=0), np.linalg.inv(cov)))
    return clusters or [(border.mean(axis=0), np.linalg.inv(np.cov(border.T) + np.eye(3) * 12.0))]


def _foreground_prior(rgb: np.ndarray) -> np.ndarray:
    """Probability each pixel belongs to the product, before GrabCut.

    Three cheap, independent signals:
      * distance from every background colour found at the border
      * a centre prior (people frame the thing they are photographing)
      * edge density (products carry detail; walls and cloth backdrops do not)
    """
    h, w = rgb.shape[:2]
    img = rgb.astype(np.float32)

    band = max(4, int(min(h, w) * 0.05))
    border = np.concatenate([
        img[:band].reshape(-1, 3), img[-band:].reshape(-1, 3),
        img[:, :band].reshape(-1, 3), img[:, -band:].reshape(-1, 3),
    ])
    flat = img.reshape(-1, 3)
    # Distance to the NEAREST background colour — a pixel only counts as
    # foreground if it is unlike every background the border showed us.
    nearest = None
    for mean, inv in _background_clusters(border):
        diff = flat - mean
        d = np.sqrt(np.einsum('ij,jk,ik->i', diff, inv, diff))
        nearest = d if nearest is None else np.minimum(nearest, d)
    colour_score = np.clip(nearest.reshape(h, w) / 5.0, 0, 1)

    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h / 2, w / 2
    centre = np.exp(-(((yy - cy) / (h * 0.42)) ** 2 + ((xx - cx) / (w * 0.42)) ** 2))

    if HAS_CV2:
        grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        edges = cv2.Laplacian(grey, cv2.CV_32F, ksize=3)
        detail = cv2.GaussianBlur(np.abs(edges), (0, 0), max(h, w) / 90)
    else:
        grey = rgb @ np.array([0.299, 0.587, 0.114])
        gy, gx = np.gradient(grey)
        detail = np.abs(gx) + np.abs(gy)
    detail = detail / (detail.max() + 1e-6)

    score = colour_score * 0.58 + centre * 0.27 + np.clip(detail * 2.2, 0, 1) * 0.15
    return np.clip(score, 0, 1)


def _largest_component(mask: np.ndarray) -> np.ndarray:
    """Keep the main subject; drop the stray blob in the corner."""
    if not HAS_CV2:
        return mask
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if count <= 1:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    biggest = int(np.argmax(areas)) + 1
    keep = (labels == biggest)
    # A second blob that is nearly as large is usually a real part of the
    # product (a lid, a second earring) — keep anything over 30% of the main.
    for idx in range(1, count):
        if idx != biggest and stats[idx, cv2.CC_STAT_AREA] > areas.max() * 0.3:
            keep |= (labels == idx)
    return keep.astype(np.uint8)


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    if not HAS_CV2:
        return mask
    flood = mask.copy()
    h, w = mask.shape
    pad = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood, pad, (0, 0), 1)
    return (mask | (1 - flood)).astype(np.uint8)


def _separation(rgb: np.ndarray, binary: np.ndarray) -> tuple[float, float]:
    """How distinct the kept region is from the discarded one.

    Returns (absolute Lab distance, distance relative to the image's own
    contrast). Both are needed, and neither works alone:

      * absolute alone rejects a correctly-cut product in a dim photo, where
        everything is compressed into a few Lab units;
      * relative alone accepts a product that fills the frame, where the two
        "sides" of the cut differ a little simply because the product is
        patterned.

    Together they say: the two sides must differ, AND they must differ by more
    than the picture differs from itself.
    """
    fg = binary.astype(bool)
    if fg.sum() < 32 or (~fg).sum() < 32:
        return 0.0, 0.0
    lab = (cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB) if HAS_CV2 else rgb).astype(np.float32)
    distance = float(np.linalg.norm(lab[fg].mean(axis=0) - lab[~fg].mean(axis=0)))
    spread = float(np.mean(np.std(lab.reshape(-1, 3), axis=0)))
    return distance, distance / max(spread, 1e-6)


def _segment(rgb: np.ndarray) -> tuple[np.ndarray, float, int]:
    """Return (alpha 0..1, coverage fraction, confidence 0-100)."""
    h, w = rgb.shape[:2]
    prior = _foreground_prior(rgb)

    if not HAS_CV2:
        alpha = (prior > 0.45).astype(np.float32)
        coverage = float(alpha.mean())
        return alpha, coverage, 45

    # Seed GrabCut from the prior instead of a blind rectangle — a rectangle
    # assumes the product is centred and fills the frame, which phone photos
    # of a saree laid on a bed simply do not.
    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    mask[prior > 0.42] = cv2.GC_PR_FGD
    mask[prior > 0.72] = cv2.GC_FGD
    border = np.zeros((h, w), bool)
    band = max(3, int(min(h, w) * 0.03))
    border[:band] = border[-band:] = True
    border[:, :band] = border[:, -band:] = True
    mask[border & (prior < 0.30)] = cv2.GC_BGD

    if not (mask == cv2.GC_FGD).any() or not (mask == cv2.GC_BGD).any():
        # Degenerate seeding (very flat image) — GrabCut would throw.
        alpha = (prior > 0.45).astype(np.float32)
        return alpha, float(alpha.mean()), 35

    try:
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(rgb, mask, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        alpha = (prior > 0.45).astype(np.float32)
        return alpha, float(alpha.mean()), 35

    binary = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    k = max(3, int(min(h, w) * 0.012) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = _fill_holes(_largest_component(binary))

    coverage = float(binary.mean())

    # How much do GrabCut and the prior agree? Disagreement means the
    # background was genuinely cluttered and the cut is not trustworthy.
    agreement = float(((binary == 1) == (prior > 0.45)).mean())
    confidence = int(np.clip(agreement * 105 - 8, 10, 96))

    # A small product on a clean sweep is a perfectly good cut-out, so coverage
    # alone proves nothing. What matters is whether the two sides of the cut
    # are actually different colours.
    distance, relative = _separation(rgb, binary)
    if distance < 3.0 or relative < 0.9:
        # Either the two sides are the same colour, or the "background" is as
        # varied as the product — which means the product fills the frame.
        confidence = min(confidence, 22)
    elif distance < 10 or relative < 1.6:
        confidence = min(confidence, 58)
    if coverage > 0.97:
        confidence = min(confidence, 25)

    # Feather so the composite does not show a cut-out halo.
    alpha = cv2.GaussianBlur(binary.astype(np.float32), (0, 0), max(1.0, min(h, w) / 260))
    return np.clip(alpha, 0, 1), coverage, confidence


# ---------------------------------------------------------------------------
# stage 3 — compose and frame
# ---------------------------------------------------------------------------
def _compose(rgb: np.ndarray, alpha: np.ndarray, background: str) -> Image.Image:
    """Place the cut-out subject on the chosen backdrop."""
    h, w = rgb.shape[:2]
    a = alpha[..., None]

    if background == "transparent":
        rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
        return Image.fromarray(rgba, "RGBA")

    if background == "studio":
        # A soft vertical gradient with a contact shadow — the look of a
        # tabletop product shot, and it reads as premium on a listing card.
        top, bottom = np.array([252, 250, 246]), np.array([226, 220, 208])
        ramp = np.linspace(0, 1, h)[:, None, None]
        canvas = (top * (1 - ramp) + bottom * ramp).astype(np.float32)
        canvas = np.repeat(canvas, w, axis=1)
        if HAS_CV2:
            ys = np.where(alpha.max(axis=1) > 0.5)[0]
            if len(ys):
                # A contact shadow, not a stage spotlight: a thin ellipse under
                # the base, heavily blurred and kept faint.
                foot = min(h - 1, int(ys.max()))
                xs = np.where(alpha[max(0, foot - 12):foot + 1].max(axis=0) > 0.5)[0]
                shadow = np.zeros((h, w), np.float32)
                if len(xs):
                    cx = int((xs.min() + xs.max()) / 2)
                    rx = max(8, int((xs.max() - xs.min()) * 0.52))
                    ry = max(4, int(min(h, w) * 0.022))
                    cv2.ellipse(shadow, (cx, min(h - 1, foot + ry // 2)),
                                (rx, ry), 0, 0, 360, 1.0, -1)
                    shadow = cv2.GaussianBlur(shadow, (0, 0), max(5.0, min(h, w) / 70))
                canvas *= (1 - 0.17 * shadow[..., None])
    else:  # white
        canvas = np.full((h, w, 3), 255.0, np.float32)

    out = rgb.astype(np.float32) * a + canvas * (1 - a)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _frame(image: Image.Image, alpha: np.ndarray, size: int = OUTPUT_SIZE) -> Image.Image:
    """Crop to the product, pad it, square it, and resize to the master size."""
    ys, xs = np.where(alpha > 0.5)
    if len(ys) == 0 or len(xs) == 0:
        box = (0, 0, image.width, image.height)
    else:
        pad_y = int(alpha.shape[0] * SUBJECT_PADDING)
        pad_x = int(alpha.shape[1] * SUBJECT_PADDING)
        box = (max(0, int(xs.min()) - pad_x), max(0, int(ys.min()) - pad_y),
               min(image.width, int(xs.max()) + pad_x), min(image.height, int(ys.max()) + pad_y))

    cropped = image.crop(box)
    side = max(cropped.width, cropped.height)
    fill = (255, 255, 255, 0) if cropped.mode == "RGBA" else (255, 255, 255)
    square = Image.new(cropped.mode, (side, side), fill)
    square.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2))
    return square.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# the pipeline
# ---------------------------------------------------------------------------
def enhance(
    data: bytes,
    *,
    background: str = "white",
    remove_background: bool = True,
) -> tuple[bytes, bytes, StudioResult]:
    """Return (original_png, enhanced_png, report)."""
    result = StudioResult()
    try:
        source = Image.open(io.BytesIO(data))
        source = ImageOps.exif_transpose(source)   # phones lie about orientation
        source = source.convert("RGB")
    except Exception as exc:
        return b"", b"", StudioResult(ok=False, note=f"Could not read that image: {exc}")

    original = source.copy()
    original.thumbnail((OUTPUT_SIZE, OUTPUT_SIZE))

    work = source.copy()
    work.thumbnail((WORK_SIZE, WORK_SIZE))
    rgb = np.array(work)

    result.brightness_before = round(_brightness(rgb), 1)
    result.sharpness_before = round(_sharpness(rgb), 1)

    # --- subject first ----------------------------------------------------
    # Segmentation comes before colour work, because every colour decision
    # below should be measured on the product rather than on the room it
    # happened to be photographed in.
    alpha = np.ones(rgb.shape[:2], np.float32)
    coverage, confidence = 1.0, 0
    if remove_background:
        # A mild lift first, purely so GrabCut can see into the shadows.
        lifted, _, _ = _exposure_and_contrast(rgb, None)
        alpha, coverage, confidence = _segment(lifted)
        usable = confidence >= 40 and 0.004 < coverage < 0.94
        result.background_removed = usable
        result.steps.append(StudioStep(
            "background", "Background removed", "बैकग्राउंड हटाया",
            applied=usable,
            detail=(f"Product isolated and placed on a clean {background} backdrop "
                    f"({confidence}% confidence)"
                    if usable else
                    "The background was too close in colour to the product to cut out "
                    "safely, so it was left in place. Shoot against a plain white cloth "
                    "for a clean cut-out."),
            detail_hi=(f"सामान अलग करके साफ़ बैकग्राउंड पर रखा ({confidence}% भरोसा)"
                       if usable else
                       "बैकग्राउंड और सामान का रंग मिल रहा था, इसलिए नहीं हटाया। "
                       "सादे सफ़ेद कपड़े पर फोटो लीजिए।"),
        ))
        if not usable:
            alpha = np.ones(rgb.shape[:2], np.float32)
            coverage = 1.0

    result.subject_coverage = round(coverage, 4)
    result.segmentation_confidence = confidence
    subject_mask = alpha if result.background_removed else None

    # --- then colour, measured on the product ------------------------------
    balanced, cast = _white_balance(rgb, subject_mask)
    if cast <= 0.03:
        balanced = rgb
    result.steps.insert(0, StudioStep(
        "white_balance", "Colour cast corrected", "रंग सुधारा",
        applied=cast > 0.03,
        detail=f"Removed a {int(cast * 100)}% colour cast from the light source",
        detail_hi=f"रोशनी से आया {int(cast * 100)}% रंग का असर हटाया",
    ))

    lit, before_brightness, gamma_applied = _exposure_and_contrast(balanced, subject_mask)
    result.steps.insert(1, StudioStep(
        "lighting", "Lighting corrected", "रोशनी ठीक की",
        applied=True,
        detail=(f"Product brightness lifted from {before_brightness:.0f} to a studio level"
                if gamma_applied else "Exposure kept, local contrast added"),
        detail_hi=("अँधेरी फोटो को स्टूडियो जैसी रोशनी दी"
                   if gamma_applied else "कंट्रास्ट बेहतर किया"),
    ))

    lit = _saturation(lit)
    lit = _unsharp(lit)
    result.steps.insert(2, StudioStep(
        "sharpen", "Detail sharpened", "बारीकी निखारी",
        applied=True,
        detail="Weave and motif detail brought forward with unsharp masking",
        detail_hi="बुनाई और डिज़ाइन की बारीकी उभारी",
    ))

    composed = _compose(lit, alpha, background if result.background_removed else "white")
    framed = _frame(composed, alpha, OUTPUT_SIZE)
    result.steps.append(StudioStep(
        "framing", "Framed for e-commerce", "ई-कॉमर्स के नाप में",
        applied=True,
        detail=f"Cropped to the product and squared to {OUTPUT_SIZE}x{OUTPUT_SIZE}, "
               f"the size marketplaces ask for",
        detail_hi=f"सामान पर काटकर {OUTPUT_SIZE}x{OUTPUT_SIZE} वर्गाकार बनाया",
    ))

    # Report the product's brightness, not the white card it now sits on.
    result.brightness_after = round(
        float(np.mean(_subject_pixels(lit, subject_mask) @ np.array([0.299, 0.587, 0.114]))), 1)
    result.brightness_before = round(
        float(np.mean(_subject_pixels(rgb, subject_mask) @ np.array([0.299, 0.587, 0.114]))), 1)
    result.sharpness_after = round(_sharpness(lit), 1)
    result.width, result.height = framed.size
    result.engine = "pavhan-studio-cv (OpenCV GrabCut)" if HAS_CV2 else "pavhan-studio-numpy"

    before_buf, after_buf = io.BytesIO(), io.BytesIO()
    original.save(before_buf, "JPEG", quality=88)
    framed.save(after_buf, "PNG" if framed.mode == "RGBA" else "JPEG",
                quality=92, optimize=True)
    return before_buf.getvalue(), after_buf.getvalue(), result
