"""Carrying a fair's footfall into the rest of the year.

The problem statement's own framing: exhibitions give "a temporary boost in
sales", and what is missing is "continuous, year-round access". A visitor who
admires a piece at Surajkund has no way to find that weaver again in March —
the relationship ends when the stall comes down.

A stall QR fixes exactly that, and nothing more. Scan it, and the artisan's
storefront is on your phone permanently. The counter on the artisan's side
then measures the thing the ministry cares about: how much of a fair's
attention turned into sales *after* the fair closed.
"""

from __future__ import annotations

import io
import secrets
from datetime import datetime, timezone

# The fairs the problem statement itself names, plus the two other national
# platforms MoSJE and Ministry of Textiles beneficiaries are commonly given
# stalls at. Footfall figures are the organisers' published claims.
KNOWN_FAIRS = [
    {"name": "Shilp Samagam", "name_hi": "शिल्प समागम",
     "venue": "Rotating — state capitals", "city": "Multi-city",
     "organiser": "Ministry of Social Justice and Empowerment",
     "annual_footfall": 150000,
     "note": "MoSJE's own national craft exposition for SC, ST, OBC and "
             "Divyangjan artisans financed by its corporations."},
    {"name": "Surajkund International Crafts Mela", "name_hi": "सूरजकुंड मेला",
     "venue": "Surajkund", "city": "Faridabad, Haryana",
     "organiser": "Haryana Tourism with Ministry of Textiles",
     "annual_footfall": 1200000,
     "note": "Runs for a fortnight each February."},
    {"name": "Dilli Haat", "name_hi": "दिल्ली हाट",
     "venue": "INA / Janakpuri / Pitampura", "city": "New Delhi",
     "organiser": "Delhi Tourism",
     "annual_footfall": 900000,
     "note": "Rotating fifteen-day stall allotments through the year."},
    {"name": "India International Trade Fair", "name_hi": "भारत अंतर्राष्ट्रीय व्यापार मेला",
     "venue": "Bharat Mandapam, Pragati Maidan", "city": "New Delhi",
     "organiser": "India Trade Promotion Organisation",
     "annual_footfall": 1000000,
     "note": "Every November; state pavilions host artisan clusters."},
    {"name": "Hunar Haat", "name_hi": "हुनर हाट",
     "venue": "Rotating", "city": "Multi-city",
     "organiser": "Ministry of Minority Affairs",
     "annual_footfall": 300000,
     "note": "Travelling exposition for master artisans and craftspeople."},
]


def new_code() -> str:
    """A short, unambiguous stall code.

    No 0/O or 1/I/L: this gets read off a printed card in a crowded hall, and
    sometimes typed by hand when a camera will not focus.
    """
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def stall_url(base_url: str, code: str) -> str:
    return f"{base_url.rstrip('/')}/s/{code}"


def qr_svg(data: str, *, scale: int = 8) -> str:
    """The stall QR as SVG, so it prints sharply at any size.

    SVG rather than PNG because these get printed on A4 and taped to a stall
    frame, and a rasterised QR at the wrong size is a QR that will not scan.
    """
    try:
        import qrcode
    except ImportError:  # pragma: no cover
        return ""

    qr = qrcode.QRCode(
        version=None,
        # High correction: a card taped to a stall gets creased, smudged and
        # partly obscured by whatever is hanging in front of it.
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1, border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    size = len(matrix)
    dimension = size * scale

    cells = []
    for y, row in enumerate(matrix):
        run_start = None
        for x, filled in enumerate([*row, False]):
            if filled and run_start is None:
                run_start = x
            elif not filled and run_start is not None:
                # Emit a run of dark modules as one rect — keeps the SVG small
                # enough to inline in a response.
                cells.append(
                    f'<rect x="{run_start * scale}" y="{y * scale}" '
                    f'width="{(x - run_start) * scale}" height="{scale}"/>')
                run_start = None

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{dimension}" '
        f'height="{dimension}" viewBox="0 0 {dimension} {dimension}" '
        f'shape-rendering="crispEdges">'
        f'<rect width="{dimension}" height="{dimension}" fill="#ffffff"/>'
        f'<g fill="#161B33">{"".join(cells)}</g></svg>'
    )


def fair_window(exhibition) -> dict:
    """Whether a fair is upcoming, running or finished."""
    now = datetime.now(timezone.utc)
    starts = exhibition.starts_on
    ends = exhibition.ends_on
    if starts and starts.tzinfo is None:
        starts = starts.replace(tzinfo=timezone.utc)
    if ends and ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)

    if starts and now < starts:
        return {"state": "upcoming", "days": (starts - now).days}
    if ends and now > ends:
        return {"state": "finished", "days": (now - ends).days}
    return {"state": "running", "days": 0}
