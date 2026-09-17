"""The order nobody could take alone.

MoSJE does not fund artisans one at a time. It funds them through self-help
groups and clusters, and the problem statement's own target is a *demographic*,
not an individual. Yet every marketplace — this one included, until now — asks
a single artisan to quote for a single order, which means the orders actually
worth having are the ones they all have to refuse.

Six weavers in Bhadohi who can each finish seventy dhurries a month cannot
individually answer a buyer wanting four hundred in six weeks. As a pool they
answer it comfortably, and each one is still paid for exactly the pieces they
made.

Three things make that fair rather than merely possible:

* **Capacity is measured, not assumed.** An allocation larger than what an
  artisan can actually finish is not generosity, it is a missed deadline with
  their name on it.
* **The rounding is largest-remainder.** Proportional shares almost never come
  out whole, and quietly giving every leftover piece to the lead artisan is
  how a cluster stops trusting a platform. Leftovers go to whoever was rounded
  down hardest.
* **The coordination share is visible.** Somebody collects the pieces, checks
  them and hands them to the carrier, and that is real work that deserves
  paying for. It is charged openly, shown to every member in rupees, and can
  be switched off.

A pool that cannot cover the quantity says so and reports the shortfall. It
does not quietly quote for less than the buyer asked for.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# What the lead artisan is paid for collecting, checking and despatching the
# whole consignment. Deliberately small and deliberately visible.
COORDINATION_SHARE = 0.03

# Same platform fee the rest of the pipeline applies. Imported as a number
# rather than a call so this module stays pure and testable.
PLATFORM_FEE_RATE = 0.05

# When an artisan has never stated a capacity, infer one from how long their
# own listings say a piece takes. A 7-day lead time on a focused craft is
# roughly four pieces a month; the floor stops a single slow showpiece from
# implying they can make nothing.
FALLBACK_CAPACITY = 8


@dataclass
class Member:
    artisan_id: str
    name: str = ""
    cluster: str = ""
    shg_name: str = ""
    capacity_month: int = 0
    lead_time_days: int = 15
    is_lead: bool = False

    # Filled by allocate()
    capacity_window: int = 0
    allocated: int = 0
    payout: float = 0.0
    coordination: float = 0.0
    note: str = ""
    note_hi: str = ""


def capacity_in_window(monthly: int, delivery_days: int) -> int:
    """How many pieces this artisan can finish before the buyer's deadline.

    Rounded *down*. A pool that promises the ceiling of everyone's capacity
    delivers late, and a cluster that delivers late does not get a second
    order.
    """
    monthly = max(0, int(monthly or 0))
    days = max(1, int(delivery_days or 30))
    return int(monthly * days / 30.0)


def infer_capacity(product_count: int, lead_time_days: int) -> int:
    """A capacity for an artisan who has never stated one."""
    if product_count <= 0:
        return FALLBACK_CAPACITY
    lead = max(1, int(lead_time_days or 7))
    per_month = max(2, int(30 / lead))
    # More distinct listings implies a working line rather than one-offs.
    return max(FALLBACK_CAPACITY, per_month * min(product_count, 4))


def allocate(quantity: int, members: list[Member], delivery_days: int) -> dict:
    """Split `quantity` across the pool, in proportion to what each can make.

    Largest-remainder rounding: everyone gets their proportional whole share,
    and the pieces left over by rounding go to the members whose fractional
    share was biggest. That is the same method used to allot seats from vote
    shares, and it has the property that matters here — no member is
    systematically shortchanged, and the parts always add up to the whole.
    """
    quantity = max(0, int(quantity or 0))
    for m in members:
        m.capacity_window = capacity_in_window(m.capacity_month, delivery_days)
        m.allocated = 0

    usable = [m for m in members if m.capacity_window > 0]
    total_capacity = sum(m.capacity_window for m in usable)

    if not usable or total_capacity == 0:
        return {"quantity": quantity, "allocated": 0, "shortfall": quantity,
                "total_capacity": 0, "members": members}

    if total_capacity <= quantity:
        # Everyone is working flat out and it is still not enough. Give each
        # member their full capacity and report the gap honestly.
        for m in usable:
            m.allocated = m.capacity_window
        return {"quantity": quantity, "allocated": total_capacity,
                "shortfall": quantity - total_capacity,
                "total_capacity": total_capacity, "members": members}

    # Proportional share, then largest remainder for the rounding leftovers.
    exact = {m.artisan_id: quantity * m.capacity_window / total_capacity
             for m in usable}
    for m in usable:
        m.allocated = int(exact[m.artisan_id])

    leftover = quantity - sum(m.allocated for m in usable)
    by_remainder = sorted(
        usable,
        key=lambda m: (exact[m.artisan_id] - int(exact[m.artisan_id]),
                       m.capacity_window),
        reverse=True)
    i = 0
    while leftover > 0 and by_remainder:
        m = by_remainder[i % len(by_remainder)]
        # Never push anyone past what they said they can make.
        if m.allocated < m.capacity_window:
            m.allocated += 1
            leftover -= 1
        i += 1
        if i > len(by_remainder) * 4:  # everyone is at capacity
            break

    return {"quantity": quantity,
            "allocated": sum(m.allocated for m in usable),
            "shortfall": max(0, leftover),
            "total_capacity": total_capacity, "members": members}


def plan(*, quantity: int, unit_price: float, delivery_days: int,
         members: list[Member], coordination: bool = True) -> dict:
    """A complete, explained pooling plan the cluster can agree to or reject."""
    split = allocate(quantity, members, delivery_days)
    unit_price = round(float(unit_price or 0), 2)
    gross = round(split["allocated"] * unit_price, 2)
    platform_fee = round(gross * PLATFORM_FEE_RATE, 2)
    net = round(gross - platform_fee, 2)

    coord_rate = COORDINATION_SHARE if coordination else 0.0
    coord_pot = round(net * coord_rate, 2)
    distributable = round(net - coord_pot, 2)

    working = [m for m in members if m.allocated > 0]
    total_allocated = sum(m.allocated for m in working) or 1

    for m in members:
        share = m.allocated / total_allocated if m.allocated else 0.0
        m.payout = round(distributable * share, 2)
        m.coordination = 0.0
        if m.allocated:
            pct = round(100 * m.allocated / max(1, m.capacity_window))
            m.note = (f"{m.allocated} of the {m.capacity_window} pieces they can "
                      f"finish in {delivery_days} days ({pct}% of capacity)")
            m.note_hi = (f"{delivery_days} दिनों में जो {m.capacity_window} पीस "
                         f"बना सकते हैं, उनमें से {m.allocated}")
        else:
            m.note = "No allocation — no capacity inside this deadline"
            m.note_hi = "इस समय-सीमा में क्षमता नहीं, इसलिए कोई हिस्सा नहीं"

    lead = next((m for m in members if m.is_lead), None)
    if lead and coord_pot:
        lead.coordination = coord_pot
        lead.payout = round(lead.payout + coord_pot, 2)

    feasible = split["shortfall"] == 0 and split["allocated"] >= quantity

    if feasible:
        summary = (f"{len(working)} artisans together can deliver all "
                   f"{quantity} pieces in {delivery_days} days.")
        summary_hi = (f"{len(working)} कारीगर मिलकर {delivery_days} दिनों में "
                      f"पूरे {quantity} पीस दे सकते हैं।")
    else:
        summary = (f"This group can deliver {split['allocated']} of {quantity} "
                   f"pieces in {delivery_days} days — {split['shortfall']} "
                   f"short. Add members, or ask the buyer for more time.")
        summary_hi = (f"यह समूह {delivery_days} दिनों में {quantity} में से "
                      f"{split['allocated']} पीस दे सकता है — {split['shortfall']} "
                      f"कम। और सदस्य जोड़ें, या खरीदार से ज़्यादा समय माँगें।")

    return {
        "feasible": feasible,
        "quantity": quantity,
        "allocated": split["allocated"],
        "shortfall": split["shortfall"],
        "total_capacity": split["total_capacity"],
        "headroom": max(0, split["total_capacity"] - quantity),
        "unit_price": unit_price,
        "gross": gross,
        "platform_fee": platform_fee,
        "net": net,
        "coordination_pot": coord_pot,
        "coordination_rate": coord_rate,
        "distributable": distributable,
        "members": members,
        "summary": summary,
        "summary_hi": summary_hi,
        "fairness_note": (
            "Shares are proportional to what each artisan can finish before "
            "the deadline. Pieces left over by rounding go to whoever was "
            "rounded down hardest, not to the lead."),
        "fairness_note_hi": (
            "हिस्सा इस आधार पर है कि समय-सीमा तक कौन कितना बना सकता है। "
            "गोल करने से बचे पीस उसे मिलते हैं जिसका हिस्सा सबसे ज़्यादा घटा, "
            "मुखिया को नहीं।"),
    }
