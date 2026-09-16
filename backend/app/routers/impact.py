"""Scheme impact — what MoSJE cannot currently measure."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Enquiry, Order, Product, User
from ..services import impact as impact_service
from ..services.schemes import (
    CORPORATION_INDEX, DISCLAIMER, SKILLING_SCHEMES, SOCIAL_CATEGORIES, corporations,
)

router = APIRouter(prefix="/api/impact", tags=["impact"])


class SchemeLink(BaseModel):
    social_category: str | None = None
    corporation: str | None = None
    scheme_name: str | None = None
    beneficiary_id: str | None = None
    loan_amount: float | None = None
    baseline_monthly_income: float | None = None
    shg_name: str | None = None
    cluster: str | None = None


def _report_for(artisan: User, db: Session) -> impact_service.ImpactReport:
    products = list(db.scalars(
        select(Product).where(Product.artisan_id == artisan.id)).all())
    ids = [p.id for p in products]
    orders = list(db.scalars(select(Order).where(Order.product_id.in_(ids)))) if ids else []
    enquiries = list(db.scalars(select(Enquiry).where(Enquiry.product_id.in_(ids)))) if ids else []
    return impact_service.build(artisan, products, orders, enquiries)


@router.get("/schemes")
def schemes() -> dict:
    """The corporations and schemes an artisan can link to."""
    return {
        "corporations": corporations(),
        "skilling_schemes": SKILLING_SCHEMES,
        "social_categories": SOCIAL_CATEGORIES,
        "ministry": "Ministry of Social Justice and Empowerment",
        "ministry_hi": "सामाजिक न्याय और अधिकारिता मंत्रालय",
        "disclaimer": DISCLAIMER["en"],
        "disclaimer_hi": DISCLAIMER["hi"],
    }


@router.post("/artisan/{artisan_id}/link")
def link_scheme(artisan_id: str, payload: SchemeLink, db: Session = Depends(get_db)) -> dict:
    """Attach the assistance programme that financed this unit."""
    artisan = db.get(User, artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")
    if payload.corporation and payload.corporation not in CORPORATION_INDEX:
        raise HTTPException(400, f"Unknown corporation: {payload.corporation}")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if value not in (None, ""):
            setattr(artisan, field, value)
    db.commit()
    db.refresh(artisan)

    return {
        "linked": bool(artisan.corporation),
        "corporation": artisan.corporation,
        "scheme_name": artisan.scheme_name,
        "beneficiary_id": artisan.beneficiary_id,
        "baseline_monthly_income": artisan.baseline_monthly_income,
        "message": "Scheme linked. Your sales from here on become the record of "
                   "whether the assistance worked.",
        "message_hi": "योजना जुड़ गई। अब से आपकी बिक्री ही इस बात का सबूत बनेगी कि "
                      "सहायता से फ़र्क़ पड़ा या नहीं।",
    }


@router.get("/artisan/{artisan_id}")
def artisan_impact(artisan_id: str, db: Session = Depends(get_db)) -> dict:
    artisan = db.get(User, artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")
    report = _report_for(artisan, db)
    corp = CORPORATION_INDEX.get(artisan.corporation or "")
    return {
        **report.__dict__,
        "corporation_detail": {
            "code": corp.code, "name": corp.name, "name_hi": corp.name_hi,
            "serves": corp.serves, "serves_hi": corp.serves_hi,
        } if corp else None,
        "disclaimer": DISCLAIMER["en"],
        "disclaimer_hi": DISCLAIMER["hi"],
    }


@router.get("/ministry")
def ministry_report(db: Session = Depends(get_db)) -> dict:
    """The aggregate a ministry desk would actually open."""
    artisans = list(db.scalars(select(User).where(User.role == "artisan")).all())
    reports = [_report_for(a, db) for a in artisans]
    return {
        "ministry": "Ministry of Social Justice and Empowerment",
        "ministry_hi": "सामाजिक न्याय और अधिकारिता मंत्रालय",
        **impact_service.aggregate(reports),
        "artisans": [
            {
                "id": r.artisan_id, "name": r.artisan_name,
                "corporation": r.corporation, "scheme": r.scheme_name,
                "social_category": r.social_category,
                "beneficiary_id": r.beneficiary_id,
                "loan_amount": r.loan_amount,
                "monthly_earnings": r.monthly_earnings,
                "baseline_monthly": r.baseline_monthly,
                "uplift_percent": r.uplift_percent if r.baseline_monthly else None,
                "digital_readiness": r.digital_readiness,
                "repayment_status": r.repayment_status,
            }
            for r in sorted(reports, key=lambda r: -r.monthly_earnings)
        ],
    }


@router.get("/ministry.csv")
def ministry_csv(db: Session = Depends(get_db)) -> Response:
    """The same report as a sheet, because that is how it will be used."""
    artisans = list(db.scalars(select(User).where(User.role == "artisan")).all())
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "beneficiary_id", "artisan", "social_category", "corporation", "scheme",
        "loan_amount", "baseline_monthly_income_self_declared",
        "measured_monthly_earnings", "uplift_percent", "annualised_earnings",
        "orders", "products", "digital_readiness", "repayment_status",
    ])
    for artisan in artisans:
        r = _report_for(artisan, db)
        writer.writerow([
            r.beneficiary_id, r.artisan_name, r.social_category, r.corporation,
            r.scheme_name, r.loan_amount, r.baseline_monthly,
            r.monthly_earnings,
            r.uplift_percent if r.baseline_monthly else "",
            r.annualised_earnings, r.orders, r.products, r.digital_readiness,
            r.repayment_status,
        ])
    return Response(
        buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition":
                 'attachment; filename="pavhan-mosje-impact.csv"'},
    )
