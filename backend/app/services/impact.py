"""Did the assistance work?

MoSJE disburses money through NSFDC, NSKFDC, NBCFDC and NDFDC to set up a
handicraft unit, and then has almost no way to find out what happened to that
household's income. The evaluation that does happen is a survey — recalled
figures, years later, from people with an incentive to answer a particular way.

PAVHAN sits in a rare position: it holds the artisan's actual transactions. So
the uplift it reports is measured, not recalled, and every number below is
traceable to orders in the database.

Two honesty rules run through this module:

  * The baseline is self-declared — the artisan states what they earned before.
    It is labelled as self-declared everywhere it is used, and never presented
    as verified.
  * Everything after the baseline is transaction-derived. Where a figure is an
    estimate (annualising three months of sales, say) the method is named in
    the response rather than buried.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .schemes import CORPORATION_INDEX, DISCLAIMER, monthly_instalment

# What a trader at the door typically leaves the artisan, used as the
# counterfactual. Drawn from the same 0.42 figure the pricing engine uses for
# its middleman comparable, so the two screens cannot contradict each other.
MIDDLEMAN_SHARE = 0.42

# Above this, an uplift figure is almost always a mis-stated baseline rather
# than a result, and folding it into an average discredits the whole table.
IMPLAUSIBLE_UPLIFT = 400.0


@dataclass
class ImpactReport:
    artisan_id: str
    artisan_name: str = ""
    scheme_linked: bool = False
    corporation: str = ""
    corporation_name: str = ""
    scheme_name: str = ""
    beneficiary_id: str = ""
    social_category: str = ""

    months_active: float = 0.0
    orders: int = 0
    gross_sales: float = 0.0
    artisan_earnings: float = 0.0
    monthly_earnings: float = 0.0
    annualised_earnings: float = 0.0

    baseline_monthly: float = 0.0
    uplift_monthly: float = 0.0
    uplift_percent: float = 0.0
    annual_uplift: float = 0.0

    middleman_equivalent: float = 0.0
    kept_from_middleman: float = 0.0

    loan_amount: float = 0.0
    indicative_emi: float = 0.0
    emi_coverage: float = 0.0
    repayment_status: str = ""
    repayment_status_hi: str = ""

    products: int = 0
    buyers_reached: int = 0
    digital_readiness: int = 0
    notes: list[str] = field(default_factory=list)
    notes_hi: list[str] = field(default_factory=list)


def _months_between(start: datetime, end: datetime) -> float:
    return max(0.5, (end - start).days / 30.44)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; comparisons need one or the other."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build(artisan, products: list, orders: list, enquiries: list) -> ImpactReport:
    """One artisan's measured outcome since joining."""
    now = datetime.now(timezone.utc)
    report = ImpactReport(
        artisan_id=artisan.id,
        artisan_name=artisan.name,
        scheme_linked=bool(artisan.corporation),
        corporation=artisan.corporation or "",
        scheme_name=artisan.scheme_name or "",
        beneficiary_id=artisan.beneficiary_id or "",
        social_category=artisan.social_category or "",
        loan_amount=artisan.loan_amount or 0.0,
    )
    corp = CORPORATION_INDEX.get(artisan.corporation or "")
    report.corporation_name = corp.name if corp else ""

    # How long has this artisan actually been trading? The account row's
    # creation date is the wrong answer whenever data was imported or seeded:
    # dividing a year of sales by a half-month-old account produced monthly
    # "earnings" of lakhs and an uplift of 2,600%, which is worse than useless
    # in a ministry report because nobody will believe any of the other numbers
    # either. Take the earliest evidence of activity instead.
    candidates = [_aware(artisan.created_at)]
    candidates += [_aware(p.created_at) for p in products]
    candidates += [_aware(o.created_at) for o in orders]
    started = min((c for c in candidates if c), default=now)
    report.months_active = round(_months_between(started, now), 1)

    report.orders = len(orders)
    report.gross_sales = round(sum(o.amount for o in orders), 2)
    report.artisan_earnings = round(sum(o.artisan_payout for o in orders), 2)
    report.products = len(products)
    report.buyers_reached = len({e.buyer_id for e in enquiries})

    report.monthly_earnings = round(
        report.artisan_earnings / max(report.months_active, 0.5), 2)
    report.annualised_earnings = round(report.monthly_earnings * 12, 2)

    report.baseline_monthly = artisan.baseline_monthly_income or 0.0
    if report.baseline_monthly > 0:
        report.uplift_monthly = round(
            report.monthly_earnings - report.baseline_monthly, 2)
        report.uplift_percent = round(
            report.uplift_monthly / report.baseline_monthly * 100, 1)
        report.annual_uplift = round(report.uplift_monthly * 12, 2)
        # An implausible figure is a data problem, not a triumph. Say so on the
        # report rather than letting it travel upward unchallenged.
        if report.uplift_percent > IMPLAUSIBLE_UPLIFT:
            report.notes.append(
                f"An uplift of {report.uplift_percent:.0f}% is implausibly high and "
                f"probably means the declared baseline is wrong or the trading "
                f"period is too short to annualise. Treat it as unverified.")
            report.notes_hi.append(
                f"{report.uplift_percent:.0f}% की बढ़त बहुत ज़्यादा लगती है — या तो पुरानी "
                f"आमदनी ग़लत दर्ज है, या अभी बहुत कम समय हुआ है। इसे अपुष्ट मानिए।")

    # The counterfactual: the same pieces sold through a trader.
    report.middleman_equivalent = round(report.gross_sales * MIDDLEMAN_SHARE, 2)
    report.kept_from_middleman = round(
        report.artisan_earnings - report.middleman_equivalent, 2)

    # Can these earnings service what was borrowed?
    if report.loan_amount > 0 and corp:
        report.indicative_emi = monthly_instalment(report.loan_amount, corp.code)
        if report.indicative_emi > 0:
            report.emi_coverage = round(
                report.monthly_earnings / report.indicative_emi, 2)
            if report.emi_coverage >= 2:
                report.repayment_status = "Comfortable"
                report.repayment_status_hi = "आराम से"
            elif report.emi_coverage >= 1:
                report.repayment_status = "Manageable"
                report.repayment_status_hi = "संभल जाएगा"
            else:
                report.repayment_status = "Tight"
                report.repayment_status_hi = "मुश्किल"

    # A simple, checkable measure of whether the unit is actually digitised —
    # the PS's "improve digital literacy" goal needs something to point at.
    readiness = 0
    if report.products >= 1:
        readiness += 25
    if report.products >= 5:
        readiness += 15
    if any(p.images for p in products):
        readiness += 15
    if any(p.title_hi for p in products):
        readiness += 10
    if report.orders >= 1:
        readiness += 20
    if report.buyers_reached >= 1:
        readiness += 15
    report.digital_readiness = min(100, readiness)

    if report.months_active < 3 and report.orders:
        report.notes.append(
            f"Annual figures are projected from {report.months_active:g} months of "
            f"actual sales, not a full year.")
        report.notes_hi.append(
            f"सालाना आँकड़े {report.months_active:g} महीने की असली बिक्री से अनुमानित हैं।")
    if report.baseline_monthly <= 0:
        report.notes.append(
            "No 'before' income was recorded, so uplift cannot be computed. "
            "Ask the artisan to state it once in their profile.")
        report.notes_hi.append(
            "पहले की आमदनी दर्ज नहीं है, इसलिए बढ़त नहीं निकाली जा सकी।")
    else:
        report.notes.append(
            "The 'before' figure is self-declared by the artisan. Everything "
            "after it is derived from actual orders on the platform.")
        report.notes_hi.append(
            "'पहले' वाली आमदनी कारीगर ने खुद बताई है। बाकी सब असली बिक्री से निकला है।")
    if not report.scheme_linked:
        report.notes.append(
            "No scheme is linked, so this cannot be attributed to any "
            "assistance programme.")
        report.notes_hi.append("कोई योजना जुड़ी नहीं है।")

    return report


def aggregate(reports: list[ImpactReport]) -> dict:
    """The roll-up a ministry desk actually needs.

    Deliberately reports how many artisans each figure rests on, because a
    97% average uplift computed from two people is not a finding.
    """
    linked = [r for r in reports if r.scheme_linked]
    # Rows with an implausible uplift are counted and reported separately
    # rather than folded into the headline average, where a single bad
    # baseline would discredit the whole table.
    with_baseline = [r for r in reports
                     if r.baseline_monthly > 0 and r.uplift_percent <= IMPLAUSIBLE_UPLIFT]
    excluded = [r for r in reports
                if r.baseline_monthly > 0 and r.uplift_percent > IMPLAUSIBLE_UPLIFT]
    earning = [r for r in reports if r.artisan_earnings > 0]

    by_corporation: dict[str, dict] = {}
    for r in linked:
        row = by_corporation.setdefault(r.corporation, {
            "corporation": r.corporation,
            "corporation_name": r.corporation_name,
            "artisans": 0, "loan_disbursed": 0.0, "earnings": 0.0,
            "uplift_samples": 0, "uplift_total": 0.0,
        })
        row["artisans"] += 1
        row["loan_disbursed"] += r.loan_amount
        row["earnings"] += r.artisan_earnings
        # Same exclusion as the headline. If the breakdown folded in a row the
        # headline threw out, the two halves of the page would disagree and
        # the first person to add up the columns would stop trusting either.
        if 0 < r.baseline_monthly and r.uplift_percent <= IMPLAUSIBLE_UPLIFT:
            row["uplift_samples"] += 1
            row["uplift_total"] += r.uplift_percent

    for row in by_corporation.values():
        row["loan_disbursed"] = round(row["loan_disbursed"], 2)
        row["earnings"] = round(row["earnings"], 2)
        row["mean_uplift_percent"] = (
            round(row["uplift_total"] / row["uplift_samples"], 1)
            if row["uplift_samples"] else None)
        row["uplift_excluded"] = row["artisans"] - row["uplift_samples"]
        row.pop("uplift_total")

    by_category: dict[str, int] = {}
    for r in reports:
        if r.social_category:
            by_category[r.social_category] = by_category.get(r.social_category, 0) + 1

    total_earnings = sum(r.artisan_earnings for r in reports)
    total_middleman = sum(r.middleman_equivalent for r in reports)

    return {
        "artisans_total": len(reports),
        "artisans_scheme_linked": len(linked),
        "artisans_earning": len(earning),
        "loan_disbursed_total": round(sum(r.loan_amount for r in linked), 2),
        "earnings_total": round(total_earnings, 2),
        "kept_from_middlemen": round(total_earnings - total_middleman, 2),
        "mean_monthly_earnings": round(
            sum(r.monthly_earnings for r in earning) / len(earning), 2) if earning else 0,
        "mean_uplift_percent": round(
            sum(r.uplift_percent for r in with_baseline) / len(with_baseline), 1)
        if with_baseline else None,
        "uplift_sample_size": len(with_baseline),
        "uplift_excluded_implausible": len(excluded),
        "mean_digital_readiness": round(
            sum(r.digital_readiness for r in reports) / len(reports), 1) if reports else 0,
        "by_corporation": sorted(by_corporation.values(),
                                 key=lambda r: -r["artisans"]),
        "by_social_category": by_category,
        "method": (
            "Earnings are summed from actual orders placed on PAVHAN. Uplift "
            "compares those earnings against a self-declared pre-enrolment "
            "income and is reported only for the artisans who supplied one — "
            "the sample size is stated alongside it. Rows whose uplift exceeds "
            "400% are excluded from the mean and counted separately, because "
            "they almost always indicate a mis-stated baseline rather than a "
            "real result. Nothing here is survey recall."
        ),
        "method_hi": (
            "कमाई पावहन पर हुए असली ऑर्डर से जोड़ी गई है। बढ़त की तुलना कारीगर की खुद बताई "
            "पुरानी आमदनी से है, और यह केवल उन्हीं कारीगरों के लिए है जिन्होंने वह बताई — "
            "कितने लोगों का आँकड़ा है, यह साथ लिखा है।"
        ),
        "disclaimer": DISCLAIMER["en"],
        "disclaimer_hi": DISCLAIMER["hi"],
    }
