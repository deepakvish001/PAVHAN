"""Export a listing in the shape a government e-marketplace expects."""

from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, User
from ..services import marketplace_export as mx

router = APIRouter(prefix="/api/export", tags=["export"])

FORMATS = ("gem", "ondc", "csv", "json")


def _load(product_id: str, db: Session) -> tuple[Product, User | None]:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    artisan = db.get(User, product.artisan_id) if product.artisan_id else None
    return product, artisan


@router.get("/formats")
def formats() -> dict:
    return {
        "formats": [
            {"key": "gem", "name": "GeM Seller Catalogue",
             "description": "Government e-Marketplace product upload format",
             "description_hi": "सरकारी ई-मार्केटप्लेस का विक्रेता प्रारूप"},
            {"key": "ondc", "name": "ONDC Retail Item",
             "description": "Open Network for Digital Commerce retail item (RET10)",
             "description_hi": "ओएनडीसी खुदरा प्रारूप"},
            {"key": "csv", "name": "Spreadsheet",
             "description": "Flat CSV for portals that take a bulk upload",
             "description_hi": "बल्क अपलोड के लिए सीएसवी फ़ाइल"},
            {"key": "json", "name": "Everything",
             "description": "All formats plus the readiness report",
             "description_hi": "सभी प्रारूप और तैयारी रिपोर्ट"},
        ],
        "note": mx.INTEGRATION_NOTE["en"],
        "note_hi": mx.INTEGRATION_NOTE["hi"],
    }


@router.get("/readiness/{product_id}")
def readiness(product_id: str, db: Session = Depends(get_db)) -> dict:
    """What still has to be filled in before this could be submitted."""
    product, artisan = _load(product_id, db)
    report = mx.readiness(product, artisan)
    hsn, hsn_text = mx.hsn_for(product.category, product.material)
    return {
        "product": {"id": product.id, "title": product.title},
        **report,
        "hsn_code": hsn,
        "hsn_description": hsn_text,
        "gem_category": mx.GEM_CATEGORY.get(product.category),
        "ondc_category": mx.ONDC_CATEGORY.get(product.category),
        "note": mx.INTEGRATION_NOTE["en"],
        "note_hi": mx.INTEGRATION_NOTE["hi"],
    }


@router.get("/{product_id}")
def export_product(
    product_id: str,
    fmt: str = Query("json", alias="format"),
    download: bool = False,
    db: Session = Depends(get_db),
):
    """The submission package itself."""
    if fmt not in FORMATS:
        raise HTTPException(400, f"format must be one of {FORMATS}")
    product, artisan = _load(product_id, db)
    stem = f"pavhan-{product.id}"

    if fmt == "csv":
        header, row = mx.to_csv_rows(product, artisan)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        writer.writerow(row)
        body = buf.getvalue()
        headers = {"Content-Disposition": f'attachment; filename="{stem}.csv"'} if download else {}
        return Response(body, media_type="text/csv", headers=headers)

    if fmt == "gem":
        payload = mx.to_gem(product, artisan)
    elif fmt == "ondc":
        payload = mx.to_ondc(product, artisan)
    else:
        payload = {
            "readiness": mx.readiness(product, artisan),
            "gem": mx.to_gem(product, artisan),
            "ondc": mx.to_ondc(product, artisan),
            "note": mx.INTEGRATION_NOTE["en"],
            "note_hi": mx.INTEGRATION_NOTE["hi"],
        }

    if download:
        return Response(
            json.dumps(payload, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{stem}-{fmt}.json"'},
        )
    return payload


@router.get("/bulk/artisan/{artisan_id}")
def bulk_csv(artisan_id: str, db: Session = Depends(get_db)) -> Response:
    """Every published piece by one artisan, as a single upload sheet."""
    artisan = db.get(User, artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")
    products = list(db.scalars(
        select(Product).where(Product.artisan_id == artisan_id,
                              Product.published.is_(True))).all())
    if not products:
        raise HTTPException(404, "This artisan has no published products")

    buf = io.StringIO()
    writer = csv.writer(buf)
    header, _ = mx.to_csv_rows(products[0], artisan)
    writer.writerow(header)
    for product in products:
        writer.writerow(mx.to_csv_rows(product, artisan)[1])
    return Response(
        buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="pavhan-{artisan_id}-catalogue.csv"'},
    )
