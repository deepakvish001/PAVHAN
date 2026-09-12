"""Generate the placeholder artwork shipped with the seed catalogue.

Real photographs cannot be committed to the repo, so each seeded listing gets a
deterministic SVG that reflects its craft's actual palette and motif geometry —
a woven grid for textiles, a thrown silhouette for pottery, a line figure for
folk art. Regenerate with:  python make_seed_images.py
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).parent / "seed_media"
OUT.mkdir(exist_ok=True)

PALETTES = {
    "banarasi_silk": ("#8c1d2b", "#d4af37", "#5c0f1c"),
    "blue_pottery": ("#1c5fa8", "#f2f4f7", "#0f3c72"),
    "madhubani": ("#c9452c", "#e8b830", "#2b2118"),
    "dhokra": ("#8a6a2f", "#d9b45a", "#40331a"),
    "bamboo_cane": ("#c2a878", "#8a6f42", "#e8dcc0"),
    "pashmina": ("#d8cfc0", "#8f8578", "#f2ece2"),
    "channapatna": ("#d0492f", "#e8c63c", "#2f7a56"),
    "chikankari": ("#f4f2ec", "#cfc9bb", "#8f8878"),
    "kalamkari": ("#a8532a", "#2f3d6b", "#e8dcc4"),
    "meenakari": ("#1f7a4d", "#d4af37", "#8c1d2b"),
    "terracotta": ("#b05a35", "#8a4326", "#e0b894"),
}

KINDS = {
    "banarasi_silk": "textile", "chikankari": "textile", "pashmina": "textile",
    "kalamkari": "textile", "blue_pottery": "vessel", "terracotta": "vessel",
    "madhubani": "folk", "dhokra": "figure", "meenakari": "ornament",
    "bamboo_cane": "weave", "channapatna": "toy",
}


def textile(a: str, b: str, c: str) -> str:
    motifs = []
    for row in range(6):
        for col in range(8):
            x, y = 40 + col * 90, 60 + row * 90
            motifs.append(
                f'<g transform="translate({x},{y})">'
                f'<path d="M0,-22 C14,-14 14,14 0,22 C-14,14 -14,-14 0,-22 Z" fill="{b}" opacity="0.9"/>'
                f'<circle cx="0" cy="0" r="5" fill="{c}"/></g>'
            )
    stripes = "".join(
        f'<rect x="0" y="{y}" width="760" height="6" fill="{b}" opacity="0.35"/>'
        for y in range(0, 640, 45)
    )
    return f'<rect width="760" height="640" fill="{a}"/>{stripes}{"".join(motifs)}'


def vessel(a: str, b: str, c: str) -> str:
    petals = "".join(
        f'<ellipse cx="380" cy="330" rx="26" ry="78" fill="{b}" opacity="0.85" '
        f'transform="rotate({i * 45} 380 330)"/>'
        for i in range(8)
    )
    return (
        f'<rect width="760" height="640" fill="{b}"/>'
        f'<path d="M300,140 L460,140 L470,200 C560,250 560,470 380,540 '
        f'C200,470 200,250 290,200 Z" fill="{a}"/>'
        f'<g opacity="0.9">{petals}</g>'
        f'<circle cx="380" cy="330" r="20" fill="{c}"/>'
        f'<rect x="292" y="132" width="176" height="18" rx="9" fill="{c}"/>'
    )


def folk(a: str, b: str, c: str) -> str:
    fish = "".join(
        f'<g transform="translate({120 + (i % 3) * 230},{150 + (i // 3) * 180})">'
        f'<path d="M0,0 C40,-40 120,-40 160,0 C120,40 40,40 0,0 Z" fill="{b}" '
        f'stroke="{c}" stroke-width="5"/>'
        f'<circle cx="128" cy="-8" r="7" fill="{c}"/>'
        f'<path d="M0,0 L-34,-26 L-34,26 Z" fill="{a}" stroke="{c}" stroke-width="5"/></g>'
        for i in range(6)
    )
    border = (
        f'<rect x="14" y="14" width="732" height="612" fill="none" '
        f'stroke="{c}" stroke-width="10"/>'
        f'<rect x="34" y="34" width="692" height="572" fill="none" '
        f'stroke="{b}" stroke-width="5" stroke-dasharray="18 12"/>'
    )
    return f'<rect width="760" height="640" fill="{a}" opacity="0.18"/>{border}{fish}'


def figure(a: str, b: str, c: str) -> str:
    threads = "".join(
        f'<path d="M250,{170 + i * 14} C330,{150 + i * 14} 430,{190 + i * 14} 510,{170 + i * 14}" '
        f'stroke="{b}" stroke-width="4" fill="none" opacity="0.8"/>'
        for i in range(22)
    )
    return (
        f'<rect width="760" height="640" fill="{c}"/>'
        f'<path d="M250,470 L250,200 C250,150 330,130 380,130 C430,130 510,150 510,200 '
        f'L510,470 L460,470 L460,300 L300,300 L300,470 Z" fill="{a}"/>'
        f'<g clip-path="none">{threads}</g>'
        f'<circle cx="380" cy="105" r="46" fill="{a}"/>'
        f'<circle cx="380" cy="105" r="18" fill="{b}"/>'
    )


def ornament(a: str, b: str, c: str) -> str:
    drops = "".join(
        f'<g transform="translate({250 + i * 130},300)">'
        f'<circle cx="0" cy="-90" r="22" fill="{b}" stroke="{c}" stroke-width="4"/>'
        f'<path d="M0,-60 C70,-20 70,80 0,130 C-70,80 -70,-20 0,-60 Z" '
        f'fill="{a}" stroke="{c}" stroke-width="5"/>'
        f'<circle cx="0" cy="30" r="26" fill="{b}"/></g>'
        for i in range(2)
    )
    return f'<rect width="760" height="640" fill="{c}" opacity="0.15"/>{drops}'


def weave(a: str, b: str, c: str) -> str:
    warp = "".join(
        f'<rect x="{x}" y="80" width="26" height="480" fill="{a}" opacity="0.9"/>'
        for x in range(80, 700, 44)
    )
    weft = "".join(
        f'<rect x="80" y="{y}" width="600" height="18" fill="{b}" opacity="0.55"/>'
        for y in range(90, 560, 40)
    )
    return f'<rect width="760" height="640" fill="{c}"/>{warp}{weft}'


def toy(a: str, b: str, c: str) -> str:
    rings = "".join(
        f'<circle cx="380" cy="{180 + i * 70}" r="{110 - i * 16}" fill="'
        f'{[a, b, c][i % 3]}" stroke="#2b2118" stroke-width="4"/>'
        for i in range(5)
    )
    return f'<rect width="760" height="640" fill="#f3ece0"/>{rings}'


BUILDERS = {
    "textile": textile, "vessel": vessel, "folk": folk, "figure": figure,
    "ornament": ornament, "weave": weave, "toy": toy,
}

CATALOGUE_KEYS = [
    "banarasi_silk", "banarasi_silk", "blue_pottery", "blue_pottery",
    "madhubani", "madhubani", "dhokra", "dhokra", "bamboo_cane", "bamboo_cane",
    "pashmina", "pashmina", "channapatna", "chikankari", "kalamkari", "meenakari",
]


def build() -> int:
    written = 0
    for i, key in enumerate(CATALOGUE_KEYS):
        palette = PALETTES.get(key, ("#8a7a66", "#d4c4a8", "#3c3227"))
        kind = KINDS.get(key, "weave")
        # vary the palette slightly per index so the two pieces of the same
        # craft do not render identically
        shifted = palette if i % 2 == 0 else (palette[1], palette[0], palette[2])
        body = BUILDERS[kind](*shifted)
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 640" '
            'width="760" height="640" role="img">'
            f"{body}</svg>"
        )
        (OUT / f"{key}_{i}.svg").write_text(svg, encoding="utf-8")
        written += 1
    return written


if __name__ == "__main__":
    print(f"Wrote {build()} seed images to {OUT}")
