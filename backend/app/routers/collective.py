"""Pooling a cluster so it can answer the orders worth having.

The allocation arithmetic lives in `services/collective`. This router's job is
to find the right people to pool with, hold the plan the group agreed to, and
turn an agreed plan into an ordinary quote — so the buyer side needs no
special case, and a pooled order behaves exactly like any other order after
the moment it is accepted.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Buyer, BuyerRequirement, Pool, PoolMember, Product, Quote, User,
)
from ..services import collective as co
from ..services import share

router = APIRouter(prefix="/api/collective", tags=["collective"])


class PlanIn(BaseModel):
    requirement_id: str
    lead_artisan_id: str
    member_ids: list[str] = []
    unit_price: float = 0
    coordination: bool = True


class RespondIn(BaseModel):
    accept: bool
    note: str = ""


def _capacity(user: User, db: Session) -> tuple[int, bool]:
    """This artisan's monthly capacity, and whether they stated it themselves.

    A stated capacity always wins. An inferred one is marked as inferred, so
    the screen can ask the artisan to confirm it rather than quietly promising
    a buyer something nobody agreed to.
    """
    if user.monthly_capacity and user.monthly_capacity > 0:
        return user.monthly_capacity, True
    products = list(db.scalars(select(Product).where(
        Product.artisan_id == user.id)))
    lead = min((p.lead_time_days or 7 for p in products), default=7)
    return co.infer_capacity(len(products), lead), False


def _peers(artisan: User, db: Session) -> list[User]:
    """Who this artisan could realistically pool with.

    Same self-help group first, because that is an existing relationship with
    its own trust and its own dispute resolution. Then the same cluster, then
    the same craft in the same region. Never the whole platform: a pool of
    strangers is how a deadline gets missed and a cluster blames the app.
    """
    everyone = list(db.scalars(select(User).where(
        User.role == "artisan", User.id != artisan.id)))
    ranked = []
    for u in everyone:
        if artisan.shg_name and u.shg_name == artisan.shg_name:
            ranked.append((0, "Same self-help group", "उसी स्वयं सहायता समूह में", u))
        elif artisan.cluster and u.cluster == artisan.cluster:
            ranked.append((1, "Same cluster", "उसी क्लस्टर में", u))
        elif artisan.region and u.region == artisan.region and \
                artisan.craft_focus and u.craft_focus == artisan.craft_focus:
            ranked.append((2, f"Same craft in {u.region}", f"{u.region} में वही शिल्प", u))
    ranked.sort(key=lambda r: r[0])
    for rank, why, why_hi, u in ranked:
        u._pool_reason = why          # noqa: SLF001 - view-only annotation
        u._pool_reason_hi = why_hi    # noqa: SLF001
    return [u for _, _, _, u in ranked]


@router.get("/cluster/{artisan_id}")
def cluster(artisan_id: str, delivery_days: int = Query(30),
            db: Session = Depends(get_db)) -> dict:
    """Everyone this artisan could pool with, and what each of them can make."""
    artisan = db.get(User, artisan_id)
    if not artisan:
        raise HTTPException(404, "Artisan not found")

    own_capacity, own_stated = _capacity(artisan, db)
    peers = _peers(artisan, db)

    members = []
    for u in peers:
        cap, stated = _capacity(u, db)
        members.append({
            "artisan_id": u.id, "name": u.name, "avatar": u.avatar,
            "region": u.region, "craft_focus": u.craft_focus,
            "shg_name": u.shg_name, "cluster": u.cluster,
            "capacity_month": cap, "capacity_stated": stated,
            "capacity_window": co.capacity_in_window(cap, delivery_days),
            "reason": getattr(u, "_pool_reason", ""),
            "reason_hi": getattr(u, "_pool_reason_hi", ""),
        })

    total = co.capacity_in_window(own_capacity, delivery_days) + \
        sum(m["capacity_window"] for m in members)
    return {
        "lead": {"artisan_id": artisan.id, "name": artisan.name,
                 "shg_name": artisan.shg_name, "cluster": artisan.cluster,
                 "capacity_month": own_capacity, "capacity_stated": own_stated,
                 "capacity_window": co.capacity_in_window(own_capacity, delivery_days)},
        "members": members,
        "delivery_days": delivery_days,
        "combined_capacity": total,
        "note": (f"Together you could deliver about {total} pieces in "
                 f"{delivery_days} days."),
        "note_hi": (f"मिलकर आप {delivery_days} दिनों में लगभग {total} पीस "
                    f"दे सकते हैं।"),
    }


def _build_members(payload: PlanIn, req: BuyerRequirement,
                   db: Session) -> list[co.Member]:
    lead = db.get(User, payload.lead_artisan_id)
    if not lead:
        raise HTTPException(404, "Lead artisan not found")

    chosen_ids = [payload.lead_artisan_id] + [
        m for m in payload.member_ids if m != payload.lead_artisan_id]
    members: list[co.Member] = []
    for aid in chosen_ids:
        u = db.get(User, aid)
        if not u:
            raise HTTPException(404, f"Artisan {aid} not found")
        cap, _ = _capacity(u, db)
        members.append(co.Member(
            artisan_id=u.id, name=u.name, cluster=u.cluster,
            shg_name=u.shg_name, capacity_month=cap,
            is_lead=(u.id == payload.lead_artisan_id)))
    return members


def _member_out(m: co.Member) -> dict:
    return {
        "artisan_id": m.artisan_id, "name": m.name, "is_lead": m.is_lead,
        "capacity_month": m.capacity_month, "capacity_window": m.capacity_window,
        "allocated": m.allocated, "payout": m.payout,
        "coordination": m.coordination,
        "note": m.note, "note_hi": m.note_hi,
    }


@router.post("/plan")
def preview(payload: PlanIn, db: Session = Depends(get_db)) -> dict:
    """Work out the split before anyone commits to it."""
    req = db.get(BuyerRequirement, payload.requirement_id)
    if not req:
        raise HTTPException(404, "Requirement not found")

    members = _build_members(payload, req, db)
    unit_price = payload.unit_price or round(
        (req.budget_min + req.budget_max) / 2, 2) or req.budget_max
    result = co.plan(quantity=req.quantity, unit_price=unit_price,
                     delivery_days=req.delivery_days, members=members,
                     coordination=payload.coordination)

    buyer = db.get(Buyer, req.buyer_id)
    return {
        **{k: v for k, v in result.items() if k != "members"},
        "members": [_member_out(m) for m in result["members"]],
        "requirement": {
            "id": req.id, "title": req.title, "quantity": req.quantity,
            "delivery_days": req.delivery_days,
            "budget_min": req.budget_min, "budget_max": req.budget_max,
            "buyer": buyer.name if buyer else "",
        },
    }


@router.post("/pools", status_code=201)
def create_pool(payload: PlanIn, db: Session = Depends(get_db)) -> dict:
    """Commit a plan, and quote the buyer as one supplier."""
    req = db.get(BuyerRequirement, payload.requirement_id)
    if not req:
        raise HTTPException(404, "Requirement not found")

    members = _build_members(payload, req, db)
    unit_price = payload.unit_price or round(
        (req.budget_min + req.budget_max) / 2, 2) or req.budget_max
    result = co.plan(quantity=req.quantity, unit_price=unit_price,
                     delivery_days=req.delivery_days, members=members,
                     coordination=payload.coordination)
    if not result["feasible"]:
        # Quoting for less than the buyer asked for, without saying so, is how
        # a cluster loses a buyer permanently.
        raise HTTPException(409, result["summary"])

    lead = db.get(User, payload.lead_artisan_id)
    pool = Pool(
        requirement_id=req.id, lead_artisan_id=payload.lead_artisan_id,
        shg_name=lead.shg_name if lead else "",
        cluster=lead.cluster if lead else "",
        quantity=req.quantity, unit_price=unit_price,
        lead_time_days=req.delivery_days, status="forming",
        notes=result["summary"],
    )
    db.add(pool)
    db.flush()

    for m in result["members"]:
        db.add(PoolMember(
            pool_id=pool.id, artisan_id=m.artisan_id,
            allocated_qty=m.allocated, capacity_qty=m.capacity_window,
            payout=m.payout, is_lead=m.is_lead,
            status="accepted" if m.is_lead else "invited",
            note=m.note))
    db.commit()
    db.refresh(pool)

    invites = []
    for m in result["members"]:
        if m.is_lead or not m.allocated:
            continue
        u = db.get(User, m.artisan_id)
        invites.append({
            "artisan_id": m.artisan_id, "name": m.name,
            "whatsapp": share.wa_link(u.phone if u else "", share.pool_invite(
                lead_name=lead.name if lead else "", 
                shg_name=pool.shg_name or pool.cluster or "our group",
                quantity=pool.quantity, allocated=m.allocated,
                payout=m.payout, days=pool.lead_time_days,
                lang=(u.language if u else "hi"))),
        })

    return {"pool": _pool_out(pool, db), "invites": invites}


def _pool_out(pool: Pool, db: Session) -> dict:
    rows = list(db.scalars(select(PoolMember).where(PoolMember.pool_id == pool.id)))
    members = []
    for r in rows:
        u = db.get(User, r.artisan_id)
        members.append({
            "id": r.id, "artisan_id": r.artisan_id,
            "name": u.name if u else "", "avatar": u.avatar if u else "",
            "allocated_qty": r.allocated_qty, "capacity_qty": r.capacity_qty,
            "payout": r.payout, "status": r.status, "is_lead": r.is_lead,
            "note": r.note,
        })
    members.sort(key=lambda m: (not m["is_lead"], -m["allocated_qty"]))

    accepted = [m for m in members if m["status"] in ("accepted", "delivered", "paid")]
    committed = sum(m["allocated_qty"] for m in accepted)
    req = db.get(BuyerRequirement, pool.requirement_id)
    return {
        "id": pool.id, "requirement_id": pool.requirement_id,
        "requirement_title": req.title if req else "",
        "lead_artisan_id": pool.lead_artisan_id,
        "shg_name": pool.shg_name, "cluster": pool.cluster,
        "quantity": pool.quantity, "unit_price": pool.unit_price,
        "lead_time_days": pool.lead_time_days, "status": pool.status,
        "quote_id": pool.quote_id, "notes": pool.notes,
        "members": members,
        "committed_qty": committed,
        "pending_qty": max(0, pool.quantity - committed),
        "all_accepted": committed >= pool.quantity,
        "created_at": pool.created_at,
    }


@router.get("/pools/{pool_id}")
def get_pool(pool_id: str, db: Session = Depends(get_db)) -> dict:
    pool = db.get(Pool, pool_id)
    if not pool:
        raise HTTPException(404, "Pool not found")
    return _pool_out(pool, db)


@router.post("/pools/{pool_id}/members/{member_id}/respond")
def respond(pool_id: str, member_id: str, payload: RespondIn,
            db: Session = Depends(get_db)) -> dict:
    """A member accepts their share, or declines it.

    A decline does not silently shrink the order. The pool's shortfall becomes
    visible and the lead has to find the pieces somewhere, which is the honest
    behaviour.
    """
    member = db.get(PoolMember, member_id)
    if not member or member.pool_id != pool_id:
        raise HTTPException(404, "That member is not in this pool")
    pool = db.get(Pool, pool_id)

    member.status = "accepted" if payload.accept else "declined"
    if not payload.accept:
        member.allocated_qty = 0
        member.payout = 0
        member.note = payload.note or "Declined"
    db.commit()
    db.refresh(pool)
    return _pool_out(pool, db)


@router.post("/pools/{pool_id}/quote", status_code=201)
def submit_quote(pool_id: str, db: Session = Depends(get_db)) -> dict:
    """Send the buyer one quote from the whole pool.

    The buyer sees an ordinary quote. Everything downstream — acceptance, the
    order, the payment — works unchanged, which is the point: pooling is a
    supply-side arrangement and should not leak into the buyer's experience.
    """
    pool = db.get(Pool, pool_id)
    if not pool:
        raise HTTPException(404, "Pool not found")
    if pool.quote_id:
        raise HTTPException(409, "This pool has already quoted")

    view = _pool_out(pool, db)
    if not view["all_accepted"]:
        raise HTTPException(
            409, f"{view['pending_qty']} pieces are still unaccepted. Everyone "
                 f"has to agree before the buyer is quoted.")

    lead_product = db.scalars(select(Product).where(
        Product.artisan_id == pool.lead_artisan_id).limit(1)).first()
    quote = Quote(
        requirement_id=pool.requirement_id,
        artisan_id=pool.lead_artisan_id,
        product_id=lead_product.id if lead_product else None,
        unit_price=pool.unit_price, quantity=pool.quantity,
        lead_time_days=pool.lead_time_days,
        message=(f"Pooled quote from {pool.shg_name or pool.cluster or 'our group'} "
                 f"— {len(view['members'])} artisans, {pool.quantity} pieces."),
        status="sent",
    )
    db.add(quote)
    db.flush()
    pool.quote_id = quote.id
    pool.status = "quoted"
    db.commit()
    return {"quote_id": quote.id, "pool": _pool_out(pool, db)}


@router.get("/artisan/{artisan_id}/pools")
def artisan_pools(artisan_id: str, db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(PoolMember).where(
        PoolMember.artisan_id == artisan_id)))
    pools = []
    for r in rows:
        pool = db.get(Pool, r.pool_id)
        if pool:
            view = _pool_out(pool, db)
            view["my_membership"] = {
                "id": r.id, "allocated_qty": r.allocated_qty,
                "payout": r.payout, "status": r.status, "is_lead": r.is_lead}
            pools.append(view)
    pools.sort(key=lambda p: p["created_at"] or "", reverse=True)
    return {
        "pools": pools,
        "summary": {
            "count": len(pools),
            "invited": sum(1 for p in pools if p["my_membership"]["status"] == "invited"),
            "committed_value": round(sum(
                p["my_membership"]["payout"] for p in pools
                if p["my_membership"]["status"] in ("accepted", "delivered", "paid")), 2),
        },
    }
