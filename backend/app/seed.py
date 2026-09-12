"""Seed catalogue.

The app must never open onto an empty screen, so it ships with a realistic
starter catalogue: six artisans across six clusters, fourteen listings spanning
every craft category, and twelve B2B buyer profiles with genuinely different
sourcing rules so the matching engine has something meaningful to discriminate
between.

Prices here are produced by the same pricing engine the live flow uses, so the
seeded numbers and the generated ones are consistent.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Buyer, Order, Product, User
from .services.pricing import recommend_price
from .services.taxonomy import CRAFT_INDEX

ARTISANS = [
    dict(name="Rukhsana Bano", role="artisan", region="Varanasi", craft_focus="Banarasi Handloom Silk",
         experience_years=22, avatar="🧕", language="hi", phone="+91 90000 11111"),
    dict(name="Mohan Lal Prajapati", role="artisan", region="Jaipur", craft_focus="Jaipur Blue Pottery",
         experience_years=17, avatar="🧑‍🎨", language="hi", phone="+91 90000 22222"),
    dict(name="Sita Devi Jha", role="artisan", region="Madhubani", craft_focus="Madhubani Painting",
         experience_years=31, avatar="👩‍🎨", language="hi", phone="+91 90000 33333"),
    dict(name="Budhram Netam", role="artisan", region="Bastar", craft_focus="Dhokra Metal Craft",
         experience_years=26, avatar="🧑‍🏭", language="hi", phone="+91 90000 44444"),
    dict(name="Rita Baruah", role="artisan", region="Assam", craft_focus="Bamboo & Cane Craft",
         experience_years=12, avatar="👩‍🌾", language="en", phone="+91 90000 55555"),
    dict(name="Abdul Rashid Mir", role="artisan", region="Srinagar", craft_focus="Kashmiri Pashmina",
         experience_years=35, avatar="🧔", language="hi", phone="+91 90000 66666"),
]

# (craft_key, artisan index, noun, colour, size, weight, work_days, stock, note)
# work_days are FOCUSED working days of 6 hours each, not elapsed calendar
# days -- the pricing engine turns them straight into an hourly wage.
CATALOGUE = [
    ("banarasi_silk", 0, "Saree", "Red", "5.5 metre", "620 gram", 12, 3,
     "Kadhwa-woven with a real-zari border; the buti repeats every four inches."),
    ("banarasi_silk", 0, "Dupatta", "Indigo", "2.4 metre", "240 gram", 3, 6,
     "A lighter everyday piece on the same pit loom, woven in a single colour."),
    ("blue_pottery", 1, "Vase", "Blue", "9 x 5 inch", "780 gram", 2, 12,
     "Quartz-paste body, cobalt oxide floral work, fired twice at low heat."),
    ("blue_pottery", 1, "Dinner Plate Set", "Turquoise", "10 inch each", "1.8 kg", 4, 8,
     "Set of four. Food-safe glaze, each plate painted freehand so no two match."),
    ("madhubani", 2, "Wall Painting", "Red", "24 x 36 inch", "310 gram", 8, 4,
     "Bharni style, handmade paper, pigments ground from turmeric, indigo and soot."),
    ("madhubani", 2, "Fish Motif Panel", "Yellow", "12 x 18 inch", "140 gram", 3, 9,
     "The fish is a Mithila fertility motif, drawn in the kachni line style."),
    ("dhokra", 3, "Tribal Horse Figurine", "Gold", "8 inch tall", "820 gram", 5, 5,
     "Lost-wax cast in bell metal; the wax thread pattern is visible on the body."),
    ("dhokra", 3, "Oil Lamp", "Copper", "6 inch tall", "540 gram", 3, 7,
     "A working diya, not a decoration piece — the bowl holds 40 ml of oil."),
    ("bamboo_cane", 4, "Storage Basket", "Beige", "14 x 10 inch", "420 gram", 1, 20,
     "Split-cane weave, treated against borer, finished with a natural wax rub."),
    ("bamboo_cane", 4, "Serving Tray", "Brown", "18 x 12 inch", "610 gram", 2, 15,
     "Double-woven rim so it holds shape under weight."),
    ("pashmina", 5, "Sozni Shawl", "Cream", "2.2 x 1 metre", "210 gram", 14, 2,
     "Hand-spun pashm with sozni needlework along all four borders. Ring-passable."),
    ("pashmina", 5, "Plain Stole", "Charcoal", "2 x 0.7 metre", "150 gram", 4, 6,
     "Undyed natural charcoal fleece, no chemical processing at any stage."),
    ("channapatna", 1, "Wooden Rattle Set", "Red", "5 inch each", "180 gram", 1, 25,
     "Ivory-wood turned on a hand lathe, coloured with food-grade vegetable lac."),
    ("chikankari", 0, "Chikankari Kurta", "White", "42 inch chest", "280 gram", 6, 6,
     "Shadow work from the reverse face, 6 stitch types across the yoke."),
    ("kalamkari", 2, "Kalamkari Panel", "Rust", "30 x 20 inch", "260 gram", 6, 5,
     "Seventeen-step natural dye process; the black comes from rusted iron liquor."),
    ("meenakari", 1, "Meenakari Jhumka", "Green", "2.5 inch drop", "34 gram", 2, 18,
     "Five separate enamel firings, one for each colour in the piece."),
]

BUYERS = [
    dict(name="Fabindia Sourcing", org_type="Retail Chain", country="India", city="New Delhi",
         logo="🏬", categories=["Textiles", "Natural Fibre"],
         materials=["Cotton", "Pure Silk", "Jute", "Bamboo"],
         preferred_regions=["Varanasi", "Lucknow", "Assam", "West Bengal"],
         certifications=["Handloom Mark"], budget_min=800, budget_max=6000,
         typical_order_qty=120, max_lead_time_days=45, values_sustainability=78,
         values_gi_tag=82, repeat_buyer_score=91,
         notes="Volume buyer for store-floor textiles. Pays in 30 days, reorders quarterly."),
    dict(name="Maison Kalā, Paris", org_type="Export House", country="France", city="Paris",
         logo="🌍", categories=["Textiles", "Folk Art"],
         materials=["Pure Silk", "Pashmina Wool", "Cotton"],
         preferred_regions=["Srinagar", "Varanasi", "Madhubani"],
         certifications=["GI Certificate", "REACH"], budget_min=4000, budget_max=45000,
         typical_order_qty=25, max_lead_time_days=120, values_sustainability=88,
         values_gi_tag=95, repeat_buyer_score=76,
         notes="Luxury boutique. Wants GI paperwork and the artisan's name on every tag."),
    dict(name="Taj Hotels Procurement", org_type="Hospitality", country="India", city="Mumbai",
         logo="🏨", categories=["Pottery & Ceramics", "Metalwork", "Wood Craft"],
         materials=["Quartz Ceramic", "Brass", "Bell Metal", "Terracotta Clay"],
         preferred_regions=["Jaipur", "Bastar", "Channapatna"],
         certifications=["Food Safe"], budget_min=400, budget_max=9000,
         typical_order_qty=200, max_lead_time_days=60, values_sustainability=70,
         values_gi_tag=64, repeat_buyer_score=88,
         notes="Fits out new properties. Large repeat orders, strict on lead time."),
    dict(name="Anthropologie Home", org_type="Export House", country="USA", city="Philadelphia",
         logo="🛒", categories=["Natural Fibre", "Pottery & Ceramics", "Textiles"],
         materials=["Bamboo", "Cane", "Jute", "Cotton", "Terracotta Clay"],
         preferred_regions=["Assam", "West Bengal", "Jaipur"],
         certifications=["FSC", "Fair Trade"], budget_min=300, budget_max=5000,
         typical_order_qty=400, max_lead_time_days=90, values_sustainability=94,
         values_gi_tag=48, repeat_buyer_score=72,
         notes="Sustainability-led home decor. Needs FSC or equivalent documentation."),
    dict(name="Jaypore", org_type="Online Marketplace", country="India", city="Gurugram",
         logo="📦", categories=["Textiles", "Jewellery", "Folk Art", "Metalwork"],
         materials=["Pure Silk", "Brass", "Cotton", "Handmade Paper"],
         preferred_regions=[], certifications=[], budget_min=600, budget_max=25000,
         typical_order_qty=40, max_lead_time_days=30, values_sustainability=62,
         values_gi_tag=80, repeat_buyer_score=84,
         notes="Curated online retail. Small batches, fast turnaround, strong storytelling."),
    dict(name="Okhai (Tata Trusts)", org_type="Social Enterprise", country="India", city="Ahmedabad",
         logo="🤝", categories=["Textiles", "Natural Fibre"],
         materials=["Cotton", "Khadi", "Jute"],
         preferred_regions=["Kutch", "Assam", "West Bengal"],
         certifications=["Craftmark"], budget_min=250, budget_max=3500,
         typical_order_qty=150, max_lead_time_days=50, values_sustainability=92,
         values_gi_tag=58, repeat_buyer_score=86,
         notes="Works only with artisan collectives. Pays 50% advance."),
    dict(name="The Design Loft, Dubai", org_type="Boutique", country="UAE", city="Dubai",
         logo="🏪", categories=["Metalwork", "Jewellery", "Folk Art"],
         materials=["Brass", "Zinc Alloy", "Bell Metal"],
         preferred_regions=["Bastar", "Bidar", "Jaipur"],
         certifications=[], budget_min=2500, budget_max=60000,
         typical_order_qty=15, max_lead_time_days=75, values_sustainability=55,
         values_gi_tag=88, repeat_buyer_score=68,
         notes="High-value statement pieces for interior projects. Low volume, high margin."),
    dict(name="Good Earth", org_type="Retail Chain", country="India", city="Bengaluru",
         logo="🌿", categories=["Pottery & Ceramics", "Textiles", "Wood Craft"],
         materials=["Quartz Ceramic", "Terracotta Clay", "Pure Silk", "Wood"],
         preferred_regions=["Jaipur", "Channapatna", "Varanasi"],
         certifications=["Craftmark"], budget_min=900, budget_max=18000,
         typical_order_qty=60, max_lead_time_days=55, values_sustainability=80,
         values_gi_tag=86, repeat_buyer_score=82,
         notes="Design-led home retail. Buys collections, not single SKUs."),
    dict(name="Nordic Craft Collective", org_type="Export House", country="Sweden", city="Stockholm",
         logo="❄️", categories=["Natural Fibre", "Wood Craft", "Pottery & Ceramics"],
         materials=["Bamboo", "Cane", "Wood", "Jute"],
         preferred_regions=["Assam", "Tripura", "Channapatna"],
         certifications=["EU Toy Safety", "FSC"], budget_min=200, budget_max=4000,
         typical_order_qty=500, max_lead_time_days=110, values_sustainability=96,
         values_gi_tag=42, repeat_buyer_score=70,
         notes="Minimalist Scandinavian retail. Certification is non-negotiable."),
    dict(name="Sanskriti Gifting", org_type="Corporate Gifting", country="India", city="Pune",
         logo="🎁", categories=["Wood Craft", "Metalwork", "Natural Fibre", "Pottery & Ceramics"],
         materials=["Wood", "Brass", "Jute", "Terracotta Clay"],
         preferred_regions=[], certifications=[], budget_min=150, budget_max=2500,
         typical_order_qty=800, max_lead_time_days=35, values_sustainability=74,
         values_gi_tag=50, repeat_buyer_score=79,
         notes="Diwali and annual-day corporate gifting. Enormous volume, tight budget."),
    dict(name="Kala Kriti Museum Store", org_type="Institution", country="India", city="Hyderabad",
         logo="🏛️", categories=["Folk Art", "Metalwork", "Textiles"],
         materials=["Handmade Paper", "Canvas", "Bell Metal", "Cotton"],
         preferred_regions=["Madhubani", "Puri", "Bastar", "Nathdwara"],
         certifications=["GI Certificate"], budget_min=1200, budget_max=40000,
         typical_order_qty=12, max_lead_time_days=100, values_sustainability=60,
         values_gi_tag=98, repeat_buyer_score=64,
         notes="Buys documented, attributable work for a museum shop. Provenance is everything."),
    dict(name="Wedding Story Co.", org_type="Boutique", country="India", city="Jaipur",
         logo="💍", categories=["Textiles", "Jewellery"],
         materials=["Pure Silk", "Zari", "Brass"],
         preferred_regions=["Varanasi", "Jaipur", "Lucknow"],
         certifications=[], budget_min=3000, budget_max=80000,
         typical_order_qty=20, max_lead_time_days=65, values_sustainability=45,
         values_gi_tag=90, repeat_buyer_score=75,
         notes="Bridal trousseau curation. Seasonal spikes around the wedding calendar."),
]


def _palette_for(colour: str) -> list[dict]:
    swatch = {
        "Red": "#b0202e", "Indigo": "#303878", "Blue": "#2856a8", "Turquoise": "#40b8be",
        "Yellow": "#f0d646", "Gold": "#d4af37", "Copper": "#b87333", "Beige": "#d6c4a4",
        "Brown": "#6e4c32", "Cream": "#f0e8d2", "Charcoal": "#3c3c40", "White": "#f6f6f6",
        "Rust": "#b0562a", "Green": "#2e8b57",
    }
    return [{"name": colour, "name_hi": "", "hex": swatch.get(colour, "#8a7a66"), "share": 0.5}]


def seed(db: Session, *, force: bool = False) -> dict:
    existing = db.scalar(select(Product).limit(1))
    if existing and not force:
        return {"seeded": False, "reason": "catalogue already populated"}

    if force:
        for model in (Order, Product, Buyer, User):
            for row in db.scalars(select(model)).all():
                db.delete(row)
        db.commit()

    rng = random.Random(26060)  # deterministic demo data
    users: list[User] = []
    for spec in ARTISANS:
        user = User(**spec)
        db.add(user)
        users.append(user)
    db.flush()

    products: list[Product] = []
    now = datetime.now(timezone.utc)
    for i, (craft_key, artisan_idx, noun, colour, size, weight, days, stock, note) in enumerate(
        CATALOGUE
    ):
        craft = CRAFT_INDEX[craft_key]
        artisan = users[artisan_idx]
        complexity = round(1.05 + (i % 5) * 0.12, 2)
        price = recommend_price(
            craft, complexity=complexity, making_days=days,
            region=artisan.region, quality_score=78 + (i % 4) * 5,
        )
        title = f"{colour} {craft.name.replace(' Craft', '')} {noun}"
        # collapse any word the title already carries
        seen: set[str] = set()
        words = []
        for w in title.split():
            if w.lower() not in seen:
                seen.add(w.lower())
                words.append(w)
        title = " ".join(words)

        product = Product(
            artisan_id=artisan.id,
            title=title,
            short_description=(
                f"A handmade {craft.name.lower()} {noun.lower()} from {artisan.region}, "
                f"in {colour.lower()}."
            ),
            detailed_description=(
                f"{note} Made by {artisan.name}, who has worked in {craft.name} for "
                f"{artisan.experience_years} years in {artisan.region}. "
                f"This single piece took {days} day{'s' if days != 1 else ''} to complete. "
                f"Because it is made by hand, small variations are part of the piece."
            ),
            story=f"This piece was {craft.story_hook}.",
            craft_type=craft.name,
            category=craft.category,
            material=craft.default_material,
            colour=colour,
            region=artisan.region,
            size=size,
            weight=weight,
            care=craft.care,
            technique=craft.name.split()[0],
            price=price.recommended,
            price_floor=price.floor,
            price_premium=price.premium,
            stock=stock,
            moq=1 if stock < 10 else 5,
            lead_time_days=max(3, days + 3),
            quality_score=78 + (i % 4) * 5,
            sustainability_score=55 + (i % 6) * 7,
            gi_tagged=craft.gi_tagged,
            tags=sorted({
                craft.category.lower(), craft.name.lower(), colour.lower(),
                craft.default_material.lower(), artisan.region.lower(),
                noun.lower(), "handmade", "artisan made",
                *(["gi tagged"] if craft.gi_tagged else []),
            }),
            keywords=craft.seo_terms,
            images=[f"/seed/{craft_key}_{i}.svg"],
            palette=_palette_for(colour),
            ai_meta={
                "engine": "pavhan-seed",
                "craft_key": craft.key,
                "craft_confidence": 92,
                "transcript_facts": {"making_days": days, "colours": [colour]},
                "vision": {"complexity": complexity},
            },
            pricing_meta=price.to_dict(),
            views=rng.randint(18, 460),
            rating=round(rng.uniform(4.2, 5.0), 1),
            created_at=now - timedelta(days=rng.randint(1, 90)),
        )
        db.add(product)
        products.append(product)
    db.flush()

    for spec in BUYERS:
        db.add(Buyer(**spec))

    # A little sales history so the artisan dashboard is not all zeros.
    for product in products[:9]:
        for _ in range(rng.randint(1, 3)):
            qty = rng.randint(1, 2)
            amount = product.price * qty
            db.add(Order(
                product_id=product.id,
                customer_name=rng.choice(
                    ["Ananya R.", "Kabir S.", "Meera T.", "Devon W.", "Priya N.", "Arjun M."]
                ),
                quantity=qty, amount=amount, artisan_payout=round(amount * 0.95, 2),
                status=rng.choice(["delivered", "shipped", "placed"]),
                created_at=now - timedelta(days=rng.randint(1, 60)),
            ))

    db.commit()
    return {
        "seeded": True,
        "artisans": len(users),
        "products": len(products),
        "buyers": len(BUYERS),
    }
