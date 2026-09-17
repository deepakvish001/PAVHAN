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

from .models import (
    Buyer, BuyerRequirement, Enquiry, Exhibition, Order, Payment, Pool,
    PoolMember, Product, Quote, Shipment, StallCard, User,
)
from .services.fairs import KNOWN_FAIRS, new_code
from .services.listing import hindi_listing
from .services.pricing import recommend_price
from .services.taxonomy import CRAFT_INDEX

# Each artisan carries the assistance programme that financed their unit —
# that linkage is what lets the platform report back to the ministry whether
# the money changed anything. Baselines are the artisan's own stated figure.
ARTISANS = [
    dict(name="Rukhsana Bano", role="artisan", region="Varanasi",
         craft_focus="Banarasi Handloom Silk", experience_years=22, avatar="🧕",
         language="hi", phone="+91 90000 11111",
         social_category="OBC", corporation="NBCFDC", scheme_name="Shilp Sampada",
         beneficiary_id="NBCFDC/UP/2023/04412", loan_amount=180000,
         baseline_monthly_income=6500, cluster="Varanasi Handloom Cluster",
         shg_name="Banaras Bunkar Samiti",
         upi_vpa="rukhsana.bano@ybl", pincode="221001", monthly_capacity=70),
    dict(name="Mohan Lal Prajapati", role="artisan", region="Jaipur",
         craft_focus="Jaipur Blue Pottery", experience_years=17, avatar="🧑‍🎨",
         language="hi", phone="+91 90000 22222",
         social_category="SC", corporation="NSFDC", scheme_name="Shilpi Samridhi Yojana",
         beneficiary_id="NSFDC/RJ/2022/11907", loan_amount=250000,
         baseline_monthly_income=7200, cluster="Jaipur Blue Pottery Cluster",
         upi_vpa="mohanlal@okaxis", pincode="302001", monthly_capacity=40),
    dict(name="Sita Devi Jha", role="artisan", region="Madhubani",
         craft_focus="Madhubani Painting", experience_years=31, avatar="👩‍🎨",
         language="hi", phone="+91 90000 33333",
         social_category="SC", corporation="NSFDC", scheme_name="Mahila Samriddhi Yojana",
         beneficiary_id="NSFDC/BR/2023/08815", loan_amount=120000,
         baseline_monthly_income=4800, shg_name="Mithila Kala Mahila Samiti",
         cluster="Madhubani Painting Cluster",
         upi_vpa="sitadevi@okicici", pincode="847211", monthly_capacity=26),
    dict(name="Budhram Netam", role="artisan", region="Bastar",
         craft_focus="Dhokra Metal Craft", experience_years=26, avatar="🧑‍🏭",
         language="hi", phone="+91 90000 44444",
         social_category="ST", corporation="NSFDC", scheme_name="Term Loan",
         beneficiary_id="NSFDC/CG/2021/03329", loan_amount=200000,
         baseline_monthly_income=5400, cluster="Bastar Dhokra Cluster",
         upi_vpa="budhram@ybl", pincode="494001", monthly_capacity=22),
    dict(name="Rita Baruah", role="artisan", region="Assam",
         craft_focus="Bamboo & Cane Craft", experience_years=12, avatar="👩‍🌾",
         language="en", phone="+91 90000 55555",
         social_category="OBC", corporation="NBCFDC", scheme_name="Swarnima for Women",
         beneficiary_id="NBCFDC/AS/2024/00761", loan_amount=90000,
         baseline_monthly_income=3900, shg_name="Sualkuchi Cane Collective",
         cluster="Assam Bamboo Cluster",
         upi_vpa="rita.baruah@paytm", pincode="781103", monthly_capacity=55),
    dict(name="Abdul Rashid Mir", role="artisan", region="Srinagar",
         craft_focus="Kashmiri Pashmina", experience_years=35, avatar="🧔",
         language="hi", phone="+91 90000 66666",
         social_category="GEN", corporation="", scheme_name="",
         baseline_monthly_income=9000, cluster="Srinagar Pashmina Cluster",
         upi_vpa="rashid.mir@oksbi", pincode="190001", monthly_capacity=14),
]

# The rest of the two self-help groups.
#
# A pooling feature demonstrated on a group of one is not demonstrating
# anything, and the orders this app exists to unlock are precisely the ones a
# single artisan has to refuse. These are the neighbours who make that
# arithmetic real: they carry a stated capacity and a UPI ID, and deliberately
# no scheme linkage, so they add nothing to the ministry's impact figures that
# the ministry did not actually finance.
CLUSTER_PEERS = [
    dict(name="Shakeel Ansari", role="artisan", region="Varanasi",
         craft_focus="Banarasi Handloom Silk", experience_years=18, avatar="🧑‍🦱",
         language="hi", phone="+91 90000 77001", social_category="OBC",
         shg_name="Banaras Bunkar Samiti", cluster="Varanasi Handloom Cluster",
         upi_vpa="shakeel.ansari@ybl", pincode="221001", monthly_capacity=65),
    dict(name="Imrana Begum", role="artisan", region="Varanasi",
         craft_focus="Banarasi Handloom Silk", experience_years=9, avatar="🧕",
         language="hi", phone="+91 90000 77002", social_category="OBC",
         shg_name="Banaras Bunkar Samiti", cluster="Varanasi Handloom Cluster",
         upi_vpa="imrana@okhdfcbank", pincode="221007", monthly_capacity=42),
    dict(name="Nafees Ahmad", role="artisan", region="Varanasi",
         craft_focus="Banarasi Handloom Silk", experience_years=27, avatar="🧔",
         language="hi", phone="+91 90000 77003", social_category="OBC",
         shg_name="Banaras Bunkar Samiti", cluster="Varanasi Handloom Cluster",
         upi_vpa="nafees.ahmad@paytm", pincode="221002", monthly_capacity=88),
    dict(name="Salma Khatoon", role="artisan", region="Varanasi",
         craft_focus="Banarasi Handloom Silk", experience_years=6, avatar="👩",
         language="hi", phone="+91 90000 77004", social_category="OBC",
         shg_name="Banaras Bunkar Samiti", cluster="Varanasi Handloom Cluster",
         upi_vpa="salma.khatoon@ybl", pincode="221005", monthly_capacity=28),
    dict(name="Urmila Devi", role="artisan", region="Madhubani",
         craft_focus="Madhubani Painting", experience_years=24, avatar="👩‍🎨",
         language="hi", phone="+91 90000 77005", social_category="SC",
         shg_name="Mithila Kala Mahila Samiti", cluster="Madhubani Painting Cluster",
         upi_vpa="urmila.devi@okicici", pincode="847211", monthly_capacity=20),
    dict(name="Ranju Kumari", role="artisan", region="Madhubani",
         craft_focus="Madhubani Painting", experience_years=11, avatar="👩",
         language="hi", phone="+91 90000 77006", social_category="SC",
         shg_name="Mithila Kala Mahila Samiti", cluster="Madhubani Painting Cluster",
         upi_vpa="ranju.kumari@ybl", pincode="847212", monthly_capacity=16),
    dict(name="Phoolwati Devi", role="artisan", region="Madhubani",
         craft_focus="Madhubani Painting", experience_years=38, avatar="👵",
         language="hi", phone="+91 90000 77007", social_category="SC",
         shg_name="Mithila Kala Mahila Samiti", cluster="Madhubani Painting Cluster",
         upi_vpa="phoolwati@oksbi", pincode="847211", monthly_capacity=12),
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
        # Everything the demo creates, deleted children-first so foreign keys
        # never dangle.
        #
        # This list used to stop at Order/Product/Buyer/User, which meant
        # requirements, quotes, stalls and fairs survived every reset and
        # piled up — the smoke suite eventually found itself ranking
        # seventy-nine "open" requirements against a catalogue of sixteen.
        # A reset button that does not reset is worse than no reset button,
        # because the demo it corrupts is the one being watched.
        for model in (PoolMember, Pool, Payment, Shipment, Quote, Enquiry,
                      BuyerRequirement, StallCard, Exhibition,
                      Order, Product, Buyer, User):
            for row in db.scalars(select(model)).all():
                db.delete(row)
        db.commit()

    rng = random.Random(26090)  # deterministic demo data (SIH PS number)
    now = datetime.now(timezone.utc)
    users: list[User] = []
    for i, spec in enumerate(ARTISANS + CLUSTER_PEERS):
        # Joined between ten and eighteen months ago. Without a realistic
        # tenure, annualising their sales produces monthly income in lakhs.
        user = User(**spec, created_at=now - timedelta(days=300 + i * 25))
        db.add(user)
        users.append(user)
    db.flush()

    products: list[Product] = []
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
            # The Hindi half, built by the same functions the live voice flow
            # uses. The seed used to write English only and leave these blank,
            # so an artisan who set the app to Hindi browsed a catalogue that
            # was entirely in English — the one language the app exists to
            # avoid making them read.
            **hindi_listing(
                craft, colour=colour, region=artisan.region, noun=noun,
                size=size, weight=weight, making_days=days,
            ),
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
    for product in products:
        for _ in range(rng.randint(2, 6)):
            qty = rng.randint(1, 2)
            amount = product.price * qty
            db.add(Order(
                product_id=product.id,
                customer_name=rng.choice(
                    ["Ananya R.", "Kabir S.", "Meera T.", "Devon W.", "Priya N.", "Arjun M."]
                ),
                quantity=qty, amount=amount, artisan_payout=round(amount * 0.95, 2),
                status=rng.choice(["delivered", "delivered", "shipped", "placed"]),
                created_at=now - timedelta(days=rng.randint(5, 290)),
            ))

    db.flush()

    # --- fairs, stall cards and B2B requirements -------------------------
    now_naive = now.replace(tzinfo=None)
    exhibitions = []
    for i, fair in enumerate(KNOWN_FAIRS):
        ex = Exhibition(
            name=fair["name"], name_hi=fair["name_hi"], venue=fair["venue"],
            city=fair["city"], organiser=fair["organiser"],
            annual_footfall=fair["annual_footfall"],
            # Stagger them so the demo shows a finished fair, a running one
            # and one still to come.
            starts_on=now_naive - timedelta(days=60 - i * 30),
            ends_on=now_naive - timedelta(days=46 - i * 30),
        )
        db.add(ex)
        exhibitions.append(ex)
    db.flush()

    stall_cards = []
    for artisan, ex in zip(users[:4], exhibitions):
        card = StallCard(
            artisan_id=artisan.id, exhibition_id=ex.id, code=new_code(),
            stall_number=f"{chr(65 + rng.randint(0, 5))}-{rng.randint(10, 99)}",
            scans=rng.randint(40, 260), follows=rng.randint(12, 90),
        )
        db.add(card)
        stall_cards.append(card)

    requirement_specs = [
        ("Handwoven silk sarees for a bridal collection", "Textiles",
         "Banarasi Handloom Silk", "Pure Silk", 40, 12000, 30000, 60,
         ["Varanasi", "Kanchipuram"]),
        ("Bamboo storage baskets for store fit-out", "Natural Fibre",
         "Bamboo & Cane Craft", "Bamboo", 400, 600, 1400, 75, ["Assam", "Tripura"]),
        ("Blue pottery dinnerware for a hotel opening", "Pottery & Ceramics",
         "Jaipur Blue Pottery", "Quartz Ceramic", 200, 1800, 4500, 55, ["Jaipur"]),
        ("Madhubani panels for a museum shop", "Folk Art",
         "Madhubani Painting", "Handmade Paper", 25, 4000, 15000, 90, ["Madhubani"]),
        ("Dhokra figurines for corporate gifting", "Metalwork",
         "Dhokra Metal Craft", "Brass / Bell Metal", 300, 900, 2500, 45, []),
    ]
    buyer_rows = list(db.scalars(select(Buyer)).all())
    requirements = []
    for i, (title, cat, craft, material, qty, lo, hi, days, regions) in enumerate(
            requirement_specs):
        req = BuyerRequirement(
            buyer_id=buyer_rows[i % len(buyer_rows)].id, title=title,
            description=f"Looking for {qty} pieces. Consistent quality across the lot "
                        f"matters more than the lowest price; we reorder every season.",
            category=cat, craft_type=craft, material=material, quantity=qty,
            budget_min=lo, budget_max=hi, delivery_days=days,
            preferred_regions=regions,
            created_at=now - timedelta(days=rng.randint(1, 20)),
        )
        db.add(req)
        requirements.append(req)
    db.flush()

    # One quote already in flight, so the screen is not empty on first open.
    first_product = next((p for p in products if p.artisan_id == users[4].id), products[0])
    db.add(Quote(
        requirement_id=requirements[1].id, artisan_id=users[4].id,
        product_id=first_product.id, unit_price=880, quantity=400,
        lead_time_days=40,
        message="I can supply 400 baskets in two batches of 200, forty days for the first.",
        created_at=now - timedelta(days=3),
    ))

    db.commit()
    return {
        "seeded": True,
        "artisans": len(users),
        "products": len(products),
        "buyers": len(BUYERS),
        "fairs": len(exhibitions),
        "stalls": len(stall_cards),
        "requirements": len(requirements),
    }
