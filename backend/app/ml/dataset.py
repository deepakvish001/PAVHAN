"""Training data for the pricing model.

There is no public dataset of what Indian artisan craft actually sells for —
that is precisely the information asymmetry this project exists to fix. So the
model is trained on a simulated market whose data-generating process is
written down here in full, rather than on a scraped file of unknown quality
that would be impossible to defend.

The simulation is not the rules engine with noise added. If it were, the model
would only ever rediscover the rules. It deliberately contains effects the
rules engine does NOT model, and those are what the model has to learn:

  * diminishing returns on labour — a 200-hour piece does not fetch twice a
    100-hour piece, because buyer budgets are finite;
  * category-specific elasticity — a ₹40,000 saree is normal, a ₹40,000
    basket is not, and the ceiling differs by category;
  * interaction between GI status and export demand — a GI tag is worth far
    more on a craft foreign buyers already want than on one they do not;
  * threshold effects on listing quality — presentation barely matters below
    a point and then matters a great deal;
  * seasonal effects that differ by category — textiles spike for weddings,
    decor spikes for Diwali, and they do not peak in the same month.

Every row also carries the cost inputs an artisan can actually state, so the
served model answers the question the problem statement asks: given this
image, this description and these raw-material costs, what should it sell for?
"""

from __future__ import annotations

import math
import random

import numpy as np

from ..services.taxonomy import CRAFTS, REGION_PREMIUM, SKILL_RATE

# What each category's market will bear, and how hard it pushes back.
# elasticity < 1 compresses the top end: baskets cannot become sarees.
CATEGORY_MARKET = {
    "Textiles":            {"ceiling": 90000, "elasticity": 0.94, "floor": 350},
    "Folk Art":            {"ceiling": 60000, "elasticity": 0.88, "floor": 300},
    "Metalwork":           {"ceiling": 55000, "elasticity": 0.86, "floor": 400},
    "Jewellery":           {"ceiling": 40000, "elasticity": 0.90, "floor": 250},
    "Pottery & Ceramics":  {"ceiling": 18000, "elasticity": 0.78, "floor": 150},
    "Wood Craft":          {"ceiling": 15000, "elasticity": 0.76, "floor": 120},
    "Natural Fibre":       {"ceiling": 9000,  "elasticity": 0.70, "floor": 90},
}

# Month multipliers per category. Wedding textiles and Diwali decor do not
# peak together, and a single season curve cannot express that.
SEASON_BY_CATEGORY = {
    "Textiles":           [1.10, 1.14, 0.98, 0.94, 1.04, 0.90, 0.92, 1.02, 1.08, 1.12, 1.22, 1.12],
    "Folk Art":           [1.02, 1.00, 0.96, 0.94, 0.92, 0.90, 0.96, 1.04, 1.12, 1.24, 1.10, 1.06],
    "Metalwork":          [1.00, 0.98, 0.96, 0.94, 0.92, 0.90, 0.98, 1.06, 1.16, 1.26, 1.08, 1.04],
    "Jewellery":          [1.06, 1.10, 1.00, 1.02, 1.08, 0.94, 0.92, 1.00, 1.06, 1.18, 1.20, 1.08],
    "Pottery & Ceramics": [0.98, 0.96, 0.96, 0.96, 0.94, 0.88, 0.94, 1.04, 1.14, 1.28, 1.06, 1.00],
    "Wood Craft":         [1.00, 0.98, 0.96, 0.96, 0.94, 0.90, 0.96, 1.06, 1.14, 1.22, 1.06, 1.02],
    "Natural Fibre":      [0.98, 0.98, 1.00, 1.02, 1.02, 0.94, 0.96, 1.02, 1.08, 1.16, 1.04, 1.00],
}

CHANNELS = ["direct", "marketplace", "b2b", "export"]
CHANNEL_LIFT = {"direct": 1.00, "marketplace": 1.18, "b2b": 0.86, "export": 1.42}

FEATURES = [
    "material_cost", "labour_hours", "skill_rate", "complexity", "quality_score",
    "gi_tagged", "export_demand", "region_premium", "month_index", "category_index",
    "channel_index", "quantity", "natural_dye", "sustainability",
]

CATEGORY_INDEX = {name: i for i, name in enumerate(sorted(CATEGORY_MARKET))}
CHANNEL_INDEX = {name: i for i, name in enumerate(CHANNELS)}


def _market_price(
    *, category: str, material_cost: float, labour_hours: float, skill_rate: float,
    complexity: float, quality: int, gi: bool, export_demand: int,
    region_premium: float, month: int, channel: str, quantity: int,
    natural_dye: bool, rng: random.Random,
) -> float:
    """What this piece actually clears at, under the simulated market."""
    market = CATEGORY_MARKET[category]

    # Labour with diminishing returns. The first fifty hours are paid nearly in
    # full; beyond that each additional hour adds less to what a buyer will pay.
    paid_hours = 50 * math.log1p(labour_hours / 50) + min(labour_hours, 50) * 0.55
    labour_value = paid_hours * skill_rate * complexity

    base = material_cost * 1.35 + labour_value

    # A GI tag is worth far more where foreign demand already exists.
    if gi:
        base *= 1.05 + (export_demand / 100) * 0.30

    base *= region_premium

    # Presentation is a threshold, not a slope: below 60 it barely registers,
    # above 80 it changes which shelf the piece is considered for.
    if quality >= 80:
        base *= 1.12 + (quality - 80) * 0.004
    elif quality >= 60:
        base *= 1.0 + (quality - 60) * 0.005
    else:
        base *= 0.88

    if natural_dye:
        base *= 1.07

    base *= SEASON_BY_CATEGORY[category][month - 1]
    base *= CHANNEL_LIFT[channel]

    # Bulk buyers pay less per piece, with the discount deepening in steps.
    if quantity >= 200:
        base *= 0.68
    elif quantity >= 100:
        base *= 0.74
    elif quantity >= 50:
        base *= 0.81
    elif quantity >= 20:
        base *= 0.89

    # The category ceiling compresses the top end rather than clipping it, so
    # the model learns a smooth saturation instead of a wall.
    ceiling = market["ceiling"]
    base = ceiling * (base / ceiling) ** market["elasticity"] if base > 0 else 0
    base = max(market["floor"], base)

    # Real transactions scatter: two identical pieces sell at different prices
    # depending on who is buying. Without this the model would be overconfident.
    return float(base * rng.lognormvariate(0, 0.11))


def build(rows: int = 20000, seed: int = 26090) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Generate the training matrix."""
    rng = random.Random(seed)
    X, y = [], []

    for _ in range(rows):
        craft = rng.choice(CRAFTS)
        category = craft.category

        # Spread the inputs well beyond the seeded catalogue so the model is
        # not merely memorising our eighteen demo products.
        material_cost = max(40.0, craft.material_cost * rng.uniform(0.45, 2.1))
        labour_hours = max(1.0, craft.labour_hours * rng.uniform(0.3, 2.4))
        skill_band = rng.choices(
            ["apprentice", "skilled", "master", "heritage"],
            weights=[0.2, 0.4, 0.28, 0.12])[0]
        skill_rate = SKILL_RATE[skill_band]
        complexity = rng.uniform(0.9, 2.1)
        quality = rng.randint(30, 100)
        gi = craft.gi_tagged and rng.random() > 0.15
        export_demand = int(np.clip(craft.export_demand + rng.gauss(0, 7), 30, 99))
        region = (craft.regions[0] if craft.regions else "").lower()
        region_premium = REGION_PREMIUM.get(region, 1.0) * rng.uniform(0.97, 1.05)
        month = rng.randint(1, 12)
        channel = rng.choices(CHANNELS, weights=[0.4, 0.3, 0.2, 0.1])[0]
        quantity = rng.choices([1, 5, 20, 50, 100, 250],
                               weights=[0.45, 0.2, 0.15, 0.1, 0.07, 0.03])[0]
        natural_dye = rng.random() < 0.25
        sustainability = int(np.clip(rng.gauss(65, 15), 20, 100))

        price = _market_price(
            category=category, material_cost=material_cost, labour_hours=labour_hours,
            skill_rate=skill_rate, complexity=complexity, quality=quality, gi=gi,
            export_demand=export_demand, region_premium=region_premium, month=month,
            channel=channel, quantity=quantity, natural_dye=natural_dye, rng=rng,
        )

        X.append([
            material_cost, labour_hours, skill_rate, complexity, quality,
            int(gi), export_demand, region_premium, month,
            CATEGORY_INDEX[category], CHANNEL_INDEX[channel], quantity,
            int(natural_dye), sustainability,
        ])
        y.append(price)

    return np.array(X, dtype=np.float64), np.array(y, dtype=np.float64), FEATURES
