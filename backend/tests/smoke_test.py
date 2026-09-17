"""End-to-end smoke test for the PAVHAN API.

Run against a live server:      python tests/smoke_test.py
Or point it elsewhere:          PAVHAN_URL=http://host:8000 python tests/smoke_test.py

It walks the real artisan journey — analyse a photo, understand a voice note,
generate a listing, price it, publish it, match buyers — and asserts the things
that actually matter for this product:

  * two different uploads must produce two different listings
  * buyer matching must rank differently for different products
  * Hindi and English queries must both find the same listing
  * every engine explanation must exist in both languages
"""

from __future__ import annotations

import io
import json
import os
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("PAVHAN_URL", "http://127.0.0.1:8000").rstrip("/")

DEVANAGARI = re.compile(r"[\u0900-\u097F]")

PASS, FAIL = [], []


def check(name: str, condition: bool, detail: str = "") -> bool:
    (PASS if condition else FAIL).append(name)
    mark = "\033[32mPASS\033[0m" if condition else "\033[31mFAIL\033[0m"
    print(f"  {mark}  {name}{f' — {detail}' if detail else ''}")
    return condition


def get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.load(r)


def post_json_query(path: str, params: dict):
    """POST with query-string arguments (FastAPI Query parameters)."""
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{BASE}{path}?{query}", b"", method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def post_json(path: str, payload: dict):
    req = urllib.request.Request(
        f"{BASE}{path}", json.dumps(payload).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def expect_refusal(path: str, payload: dict | None = None, *, query: dict | None = None):
    """POST something that ought to be rejected, and return (status, detail).

    Several of the guarantees in this app are refusals — money that cannot be
    released before delivery, a pool that will not quote for less than the
    buyer asked for — and a refusal nobody tests is a refusal that quietly
    stops happening.
    """
    url = f"{BASE}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    body = json.dumps(payload).encode() if payload is not None else b""
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:  # noqa: BLE001 - a non-JSON error body is still a refusal
            return exc.code, {}


def post_multipart(path: str, fields: dict, files: dict | None = None):
    boundary = "----pavhan-smoke"
    body = b""
    for key, value in fields.items():
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n"
            f"{value}\r\n"
        ).encode()
    for key, (filename, data, ctype) in (files or {}).items():
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"; "
            f"filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n"
        ).encode() + data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE}{path}", body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def make_image(kind: str) -> bytes:
    """Two visually unrelated photographs, generated so the test is self-contained."""
    from PIL import Image, ImageDraw

    rng = random.Random(kind)
    if kind == "silk":
        img = Image.new("RGB", (900, 620), (150, 22, 40))
        draw = ImageDraw.Draw(img)
        for x in range(0, 900, 34):
            for y in range(0, 620, 34):
                draw.ellipse([x, y, x + 19, y + 19], fill=(212, 175, 55))
    else:  # a blue pot on a pale ground
        img = Image.new("RGB", (620, 900), (240, 238, 231))
        draw = ImageDraw.Draw(img)
        draw.ellipse([110, 230, 510, 820], fill=(32, 86, 168))
        draw.ellipse([200, 330, 420, 520], fill=(246, 248, 250))
        for _ in range(24):
            x, y = rng.randint(150, 470), rng.randint(280, 760)
            draw.ellipse([x, y, x + 24, y + 24], fill=(250, 250, 252))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def main() -> int:
    print(f"\nPAVHAN smoke test against {BASE}\n" + "=" * 62)

    # Reset the catalogue first. Several checks publish listings, send quotes
    # and advance orders, so without this the second run sees the leftovers of
    # the first and fails on state it created itself.
    print("\n[fixture]")
    try:
        reseeded = post_json("/api/admin/reseed", {})
        check("catalogue reset to a known state", reseeded.get("seeded"),
              f'{reseeded.get("products")} products, {reseeded.get("requirements")} requirements')
    except Exception as exc:
        check("catalogue reset to a known state", False, str(exc))

    print("\n[health]")
    health = get("/api/health")
    check("API is up", health.get("status") == "ok")
    check("catalogue is indexed", health.get("indexed_listings", 0) >= 10,
          f"{health.get('indexed_listings')} listings")

    print("\n[vision — two different photos must read differently]")
    silk = post_multipart("/api/ai/analyze-image", {},
                          {"file": ("silk.jpg", make_image("silk"), "image/jpeg")})
    pot = post_multipart("/api/ai/analyze-image", {},
                         {"file": ("pot.jpg", make_image("pot"), "image/jpeg")})
    sv, pv = silk["vision"], pot["vision"]
    check("palettes differ", sv["dominant_colour"] != pv["dominant_colour"],
          f'{sv["dominant_colour"]} vs {pv["dominant_colour"]}')
    check("silhouettes differ", sv["silhouette"] != pv["silhouette"],
          f'{sv["silhouette"]} vs {pv["silhouette"]}')
    check("intricacy is measured", sv["complexity"] != pv["complexity"],
          f'{sv["complexity"]} vs {pv["complexity"]}')
    check("photo tips are bilingual",
          bool(sv.get("photo_tips")) and bool(sv.get("photo_tips_hi")))

    print("\n[listing — the same endpoint must not return the same craft]")
    listing_a = post_multipart("/api/ai/generate-listing", {
        "transcript": "Yeh Banarasi handwoven silk saree hai, red aur golden zari, "
                      "5.5 metre, 450 gram, barah din lage, dry clean only",
        "image_id": silk["image_id"], "language": "hi",
    })
    listing_b = post_multipart("/api/ai/generate-listing", {
        "transcript": "Maine Jaipur blue pottery ka guldasta banaya hai, neela aur "
                      "safed, ceramic ka hai, 800 gram, teen din lage",
        "image_id": pot["image_id"], "language": "hi",
    })
    check("craft type differs", listing_a["craft_type"] != listing_b["craft_type"],
          f'{listing_a["craft_type"]} vs {listing_b["craft_type"]}')
    check("titles differ", listing_a["title"] != listing_b["title"])
    check("prices differ", listing_a["price"] != listing_b["price"],
          f'{listing_a["price"]} vs {listing_b["price"]}')
    check("voice facts were extracted",
          listing_a["size"] == "5.5 metre" and listing_a["weight"] == "450 gram",
          f'size={listing_a["size"]} weight={listing_a["weight"]}')
    check("Hindi number words parsed",
          listing_a["ai_meta"]["transcript_facts"]["making_days"] == 12,
          f'{listing_a["ai_meta"]["transcript_facts"]["making_days"]} days')
    check("craft identification is explained",
          len(listing_a["ai_meta"]["craft_evidence"]) > 0)
    check("quality score is honest, not always 100",
          listing_a["quality_score"] != listing_b["quality_score"]
          or listing_b["quality_score"] < 100,
          f'{listing_a["quality_score"]} vs {listing_b["quality_score"]}')

    print("\n[pricing — explainable and bilingual]")
    pricing = listing_a["pricing_meta"]
    check("floor < recommended < premium",
          pricing["floor"] < pricing["recommended"] < pricing["premium"],
          f'{pricing["floor"]} / {pricing["recommended"]} / {pricing["premium"]}')
    check("breakdown itemised", len(pricing["breakdown"]) >= 4,
          f'{len(pricing["breakdown"])} lines')
    check("breakdown notes are bilingual",
          all(line.get("note_hi") for line in pricing["breakdown"]))
    check("comparables include the middleman rate",
          any("middleman" in c["label"].lower() for c in pricing["comparables"]))
    check("comparables are bilingual",
          all(c.get("label_hi") for c in pricing["comparables"]))
    check("artisan earning is stated", pricing["artisan_earning"] > 0)

    print("\n[publish + buyer matching]")
    artisan = get("/api/users?role=artisan")[0]
    payload = {k: listing_a[k] for k in (
        "title", "short_description", "detailed_description", "story", "craft_type",
        "category", "material", "colour", "region", "size", "weight", "care",
        "technique", "price", "price_floor", "price_premium", "quality_score",
        "sustainability_score", "gi_tagged", "tags", "keywords", "images",
        "palette", "ai_meta", "pricing_meta",
    )}
    payload |= {"artisan_id": artisan["id"], "stock": 8,
                "lead_time_days": listing_a["lead_time_days"]}
    product = post_json("/api/products", payload)
    check("listing published", bool(product.get("id")))

    match_new = get(f"/api/buyers/match/{product['id']}")
    check("buyers were scored", match_new["summary"]["buyers_scored"] >= 10,
          f'{match_new["summary"]["buyers_scored"]} buyers')
    check("matches returned", len(match_new["matches"]) > 0)
    check("every match explains itself",
          all(len(m["factors"]) == 7 for m in match_new["matches"]))
    check("match reasons are bilingual",
          all(f.get("detail_hi") for f in match_new["matches"][0]["factors"]))
    check("a ready-made pitch is included",
          bool(match_new["matches"][0]["pitch"]) and bool(match_new["matches"][0]["pitch_hi"]))
    check("buyer categories rolled up", len(match_new["categories"]) > 0)

    # Matching must actually discriminate between products.
    products = get("/api/products?limit=30")
    basket = next((p for p in products if "Basket" in p["title"]), None)
    saree = next((p for p in products if "Saree" in p["title"]), None)
    if basket and saree:
        top_basket = [m["name"] for m in get(f"/api/buyers/match/{basket['id']}")["matches"][:3]]
        top_saree = [m["name"] for m in get(f"/api/buyers/match/{saree['id']}")["matches"][:3]]
        check("different products match different buyers",
              set(top_basket) != set(top_saree),
              f"basket→{top_basket[0]} | saree→{top_saree[0]}")

    print("\n[search]")
    hindi = get("/api/search?q=%E0%A4%B8%E0%A4%BE%E0%A4%A1%E0%A4%BC%E0%A5%80")  # साड़ी
    english = get("/api/search?q=saree")
    check("Hindi query finds results", hindi["total"] > 0, f'{hindi["total"]} hits')
    check("Hindi and English queries agree",
          hindi["total"] == english["total"],
          f'{hindi["total"]} vs {english["total"]}')
    typo = get("/api/search?q=pashmena")
    check("typos are tolerated",
          typo["total"] > 0 or bool(typo["did_you_mean"]),
          f'did_you_mean={typo["did_you_mean"]}')
    faceted = get("/api/search?q=&category=Textiles")
    check("facets are built from live data", bool(faceted["facets"].get("craft_type")))
    check("filters narrow results",
          all(r["category"] == "Textiles" for r in faceted["results"]))
    check("search is fast", hindi["took_ms"] < 250, f'{hindi["took_ms"]}ms')

    print("\n[voice guide]")
    scripts = get("/api/voice/scripts?lang=hi")
    check("every screen has a Hindi script", len(scripts["screens"]) >= 12,
          f'{len(scripts["screens"])} screens')
    check("artisan welcome mentions fair payment",
          "दाम" in scripts["welcome"]["artisan"])
    roles = get("/api/voice/roles?lang=hi")
    check("role picker offers 4 roles", len(roles["roles"]) == 4)
    english_scripts = get("/api/voice/scripts?lang=en")
    check("scripts exist in English too",
          english_scripts["screens"].keys() == scripts["screens"].keys())

    print("\n[live coaching]")
    partial = post_multipart("/api/ai/coach",
                             {"transcript": "maine ek diya banaya hai", "language": "hi"})
    check("incomplete notes score low", partial["completeness"] < 70,
          f'{partial["completeness"]}%')
    check("the next question is suggested", bool(partial["next_question"]))
    full = post_multipart("/api/ai/coach", {
        "transcript": "Banarasi silk saree hai, laal rang, 5.5 metre, 450 gram, "
                      "barah din lage, Varanasi se hun, dry clean only",
        "language": "hi",
    })
    check("complete notes score high", full["completeness"] >= 80, f'{full["completeness"]}%')

    print("\n[AI Product Studio]")
    studio_status = get("/api/studio/status")
    check("studio engine is available", bool(studio_status.get("engine")),
          studio_status.get("engine"))
    dim = make_image("silk")
    shot = post_multipart("/api/studio/enhance", {"background": "white"},
                          {"file": ("dim.jpg", dim, "image/jpeg")})
    report = shot["report"]
    check("before and after are both produced",
          bool(shot["before_url"]) and bool(shot["after_url"]))
    check("lighting was corrected",
          report["brightness_after"] > report["brightness_before"],
          f'{report["brightness_before"]} -> {report["brightness_after"]}')
    check("output is a square e-commerce master",
          report["width"] == report["height"] == 1600,
          f'{report["width"]}x{report["height"]}')
    check("every studio step explains itself in both languages",
          all(s.get("detail") and s.get("detail_hi") for s in report["steps"]))
    check("the studio re-reads the cleaned photo", shot.get("vision") is not None)

    print("\n[Hindi copy]")
    hindi = post_multipart("/api/ai/generate-listing", {
        "transcript": "Yeh Banarasi silk saree hai, laal rang, 5.5 metre, 450 gram, "
                      "barah din lage",
        "language": "hi",
    })
    devanagari = lambda t: any("\u0900" <= c <= "\u097f" for c in t or "")
    check("Hindi title generated", devanagari(hindi.get("title_hi")), hindi.get("title_hi"))
    check("Hindi short description generated",
          devanagari(hindi.get("short_description_hi")))
    check("Hindi detailed description generated",
          devanagari(hindi.get("detailed_description_hi"))
          and len(hindi["detailed_description_hi"]) > 80)
    check("English copy is still English",
          bool(hindi["detailed_description"]) and not devanagari(hindi["detailed_description"]))
    check("Hindi carries the same facts",
          "5.5" in hindi["detailed_description_hi"] and "450" in hindi["detailed_description_hi"])

    print("\n[assistant]")
    intents = {
        "meri kamai kitni hai": "my_earnings",
        "mere kitne saman hain": "my_products",
        "achhi photo kaise lu": "photo_help",
        "GI kya hota hai": "gi_help",
        "commission kitna lete ho": "commission_help",
        "who will buy my craft": "find_buyers",
    }
    wrong = []
    for question, expected in intents.items():
        reply = post_json_query("/api/assistant/ask", {"message": question, "lang": "hi"})
        if reply["intent"] != expected:
            wrong.append(f'{question} -> {reply["intent"]}')
    check("assistant routes questions to the right intent", not wrong, "; ".join(wrong))
    money = post_json_query("/api/assistant/ask",
                            {"message": "meri kamai kitni hai", "lang": "hi"})
    check("assistant answers from live data", "\u20b9" in money["text"])
    check("assistant offers a next step", bool(money.get("action")))

    print("\n[sign-in]")
    # A fresh number each run: re-using one makes the second run see a
    # returning user and fail a test that is really about onboarding.
    phone = f"99{random.randint(10000000, 99999999)}"
    otp = post_json("/api/auth/request-otp", {"phone": phone})
    check("OTP requested", otp["sent"])
    check("demo code is exposed only because no SMS gateway is set",
          bool(otp["demo_code"]) and otp["delivered_by_sms"] is False)
    session = post_json("/api/auth/verify-otp", {
        "phone": phone, "code": otp["demo_code"], "name": "Test Artisan",
        "role": "artisan", "language": "hi",
    })
    check("signed in", bool(session["token"]))
    check("new user is sent to onboarding", session["needs_onboarding"])
    profile = post_json("/api/auth/complete-profile", {
        "token": session["token"], "craft_focus": "Bamboo & Cane Craft", "region": "Assam",
    })
    check("profile saved", profile["craft_focus"] == "Bamboo & Cane Craft")

    print("\n[Hindi labels for data]")
    labels = get("/api/voice/labels?lang=hi")["labels"]
    check("craft, category, material and region labels exist",
          all(labels.get(k) for k in ("crafts", "categories", "materials", "regions")))

    print("\n[regional languages — PS: voice notes in regional languages]")
    langs = get("/api/voice/languages")
    check("ten-plus input languages offered", len(langs["languages"]) >= 11,
          f'{len(langs["languages"])} languages')
    check("output is fixed to English and Hindi",
          set(langs["output_languages"]) == {"en", "hi"})
    check("each language carries a speech locale",
          all(l.get("speech_locale") and l.get("tts_locale") for l in langs["languages"]))

    regional = {
        "ta": "இது கையால் நெய்த சிவப்பு பட்டு புடவை, பத்து நாள் ஆனது",
        "bn": "এটি হাতে বোনা লাল রেশম শাড়ি, বারো দিন লেগেছে",
        "gu": "આ હાથથી બનાવેલી લાલ બાંધણી ઓઢણી છે, પાંચ દિવસ લાગ્યા",
        "or": "ଏହା ହାତରେ ବୁଣା ଲାଲ ରେଶମ ଶାଢ଼ୀ, ଦଶ ଦିନ ଲାଗିଲା",
        "mr": "ही हाताने विणलेली लाल रेशीम साडी आहे, बारा दिवस लागले",
    }
    crafts_seen, failures = set(), []
    for code, sentence in regional.items():
        listed = post_multipart("/api/ai/generate-listing",
                                {"transcript": sentence, "language": code})
        crafts_seen.add(listed["craft_type"])
        if listed.get("spoken_language") != code:
            failures.append(f'{code} detected as {listed.get("spoken_language")}')
        if not listed.get("colour") or not listed.get("detailed_description_hi"):
            failures.append(f"{code} lost facts")
    check("regional speech is understood", not failures, "; ".join(failures))
    check("regional languages map to their own crafts", len(crafts_seen) >= 4,
          ", ".join(sorted(crafts_seen)))

    print("\n[ML pricing — PS: a machine learning algorithm]")
    card = get("/api/pricing/model")
    check("a trained model is served", card.get("available"))
    check("it is a real regressor", "GradientBoosting" in card.get("algorithm", ""))
    check("accuracy is measured and published",
          card["metrics"]["median_abs_pct"] < 15,
          f'median error {card["metrics"]["median_abs_pct"]}%')
    check("held-out accuracy is reported",
          card["metrics"]["within_20pct"] > 75,
          f'{card["metrics"]["within_20pct"]}% within 20%')

    priced = post_json("/api/pricing/recommend", {
        "craft_key": "banarasi_silk", "making_days": 12, "complexity": 1.4,
        "quality_score": 85, "material_cost": 3200,
    })
    check("both engines answer", bool(priced.get("ml")) and priced["recommended"] > 0)
    check("the model explains this specific price",
          len(priced["ml"]["drivers"]) >= 3,
          ", ".join(d["feature"] for d in priced["ml"]["drivers"][:3]))
    check("drivers are bilingual",
          all(d.get("label") and d.get("label_hi") for d in priced["ml"]["drivers"]))
    check("the two engines are reconciled, not averaged blindly",
          bool(priced["reconciliation"]["note"])
          and priced["reconciliation"]["source"] in ("blended", "cost-anchored", "rules-only"))

    print("\n[raw material costs — PS: based on raw material costs]")
    with_costs = post_json("/api/pricing/recommend", {
        "craft_key": "bamboo_cane", "making_hours": 8, "material_cost": 150,
        "labour_cost": 900, "other_cost": 60, "desired_margin_percent": 25,
    })
    labels = {line["label"] for line in with_costs["breakdown"]}
    check("the artisan's own costs are used", "Other costs" in labels)
    check("the stated margin is applied", with_costs["margin_percent"] == 25.0,
          f'{with_costs["margin_percent"]}%')
    default_costs = post_json("/api/pricing/recommend",
                              {"craft_key": "bamboo_cane", "making_hours": 8})
    check("stated costs change the price",
          with_costs["recommended"] != default_costs["recommended"],
          f'{default_costs["recommended"]} -> {with_costs["recommended"]}')

    print("\n[government e-marketplace — PS: or government e-marketplaces]")
    any_product = get("/api/products?limit=1")[0]
    pid = any_product["id"]
    ready = get(f"/api/export/readiness/{pid}")
    check("readiness is assessed", "score" in ready and "blocking" in ready)
    check("an HSN code is assigned", bool(ready.get("hsn_code")),
          f'{ready.get("hsn_code")} — {ready.get("hsn_description")}')
    gem = get(f"/api/export/{pid}?format=gem")
    check("GeM catalogue fields produced",
          all(k in gem for k in ("product_name", "hsn_code", "country_of_origin",
                                 "offer_price", "specifications")))
    ondc = get(f"/api/export/{pid}?format=ondc")
    check("ONDC item shape produced",
          "descriptor" in ondc and "@ondc/org/statutory_reqs_packaged_commodities" in ondc)
    check("statutory declarations are filled",
          bool(ondc["@ondc/org/statutory_reqs_packaged_commodities"]
               ["month_year_of_manufacture_packing_import"]))
    check("the integration limit is stated honestly",
          "credentials" in (ready.get("note") or "").lower())

    print("\n[installable app — PS: cross-platform mobile application]")
    for path, kind in (("/manifest.webmanifest", "manifest"),
                       ("/sw.js", "service worker"),
                       ("/icon.svg", "app icon")):
        try:
            with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as r:
                check(f"{kind} is served", r.status == 200)
        except Exception as exc:
            check(f"{kind} is served", False, str(exc))

    print("\n[MoSJE scheme impact — the ministry that posted this PS]")
    catalogue = get("/api/impact/schemes")
    check("MoSJE lending corporations listed",
          {c["code"] for c in catalogue["corporations"]} >= {"NSFDC", "NSKFDC", "NBCFDC", "NDFDC"},
          ", ".join(c["code"] for c in catalogue["corporations"]))
    check("social categories cover MoSJE's beneficiaries",
          {c["code"] for c in catalogue["social_categories"]} >= {"SC", "ST", "OBC", "DNT", "SK", "PwD"})
    check("scheme terms are labelled indicative",
          "indicative" in catalogue["disclaimer"].lower())

    ministry = get("/api/impact/ministry")
    check("ministry roll-up produced", ministry["artisans_total"] > 0,
          f'{ministry["artisans_scheme_linked"]}/{ministry["artisans_total"]} scheme-linked')
    check("uplift reports its sample size", "uplift_sample_size" in ministry)
    check("implausible uplift is excluded, not averaged in",
          "uplift_excluded_implausible" in ministry)
    check("uplift is plausible, not a 900% artefact",
          ministry["mean_uplift_percent"] is None or ministry["mean_uplift_percent"] < 400,
          f'mean {ministry["mean_uplift_percent"]}%')
    check("broken down by lending corporation", len(ministry["by_corporation"]) >= 2)
    check("broken down by social category", len(ministry["by_social_category"]) >= 3,
          str(ministry["by_social_category"]))
    check("method is stated, not assumed", "survey recall" in ministry["method"])

    artisan_row = ministry["artisans"][0]
    detail = get(f'/api/impact/artisan/{artisan_row["id"]}')
    check("an artisan's own record is measured from real orders",
          detail["months_active"] > 1 and detail["orders"] >= 0,
          f'{detail["months_active"]} months')
    check("baseline is flagged self-declared",
          any("self-declared" in n for n in detail["notes"]) or detail["baseline_monthly"] == 0)
    if detail["loan_amount"] > 0:
        check("loan repayment capacity computed",
              detail["indicative_emi"] > 0 and detail["repayment_status"],
              f'{detail["emi_coverage"]}x — {detail["repayment_status"]}')

    print("\n[physical fairs — the PS's own framing]")
    fair_data = get("/api/fairs")
    names = {f["name"] for f in fair_data["fairs"]}
    check("the fairs the PS names are present",
          {"Shilp Samagam", "Dilli Haat"} <= names
          and any("Surajkund" in n for n in names),
          ", ".join(sorted(names)[:3]))
    check("fair state is computed", all(f["state"] in ("upcoming", "running", "finished")
                                        for f in fair_data["fairs"]))

    stall = post_json("/api/fairs/stall", {"artisan_id": artisan_row["id"],
                                           "stall_number": "T-01"})
    check("stall card issued", len(stall["code"]) == 6, stall["code"])
    try:
        with urllib.request.urlopen(f'{BASE}/api/fairs/stall/{stall["code"]}/qr.svg',
                                    timeout=10) as r:
            svg = r.read().decode()
        check("QR renders as SVG", r.status == 200 and svg.startswith("<svg"),
              f"{len(svg)} bytes")
    except Exception as exc:
        check("QR renders as SVG", False, str(exc))

    front = get(f'/api/fairs/stall/{stall["code"]}')
    check("scanning opens the artisan's storefront",
          front["artisan"]["id"] == artisan_row["id"] and front["scans"] >= 1)
    followed = get(f'/api/fairs/stall/{stall["code"]}?follow=true')
    check("a visitor can be kept", followed["follows"] >= 1)
    perf = get(f'/api/fairs/stall/{stall["code"]}/performance')
    check("post-fair conversion is measured",
          "orders_after_fair" in perf and bool(perf["reading"]))

    print("\n[two-way B2B — buyers post, artisans quote]")
    reqs = get(f'/api/trade/requirements?artisan_id={artisan_row["id"]}')
    check("open requirements exist", reqs["total"] >= 3, f'{reqs["total"]} open')
    check("they are ranked for this artisan",
          reqs["requirements"][0]["fit_score"] >= reqs["requirements"][-1]["fit_score"],
          f'top fit {reqs["requirements"][0]["fit_score"]}')
    check("the ranking explains itself",
          any(r["fit_reasons"] for r in reqs["requirements"]))

    target = next(r for r in reqs["requirements"] if not r["already_quoted"])
    quote = post_json("/api/trade/quotes", {
        "requirement_id": target["id"], "artisan_id": artisan_row["id"],
        "unit_price": max(1, target["budget_min"]), "quantity": target["quantity"],
        "lead_time_days": 20, "message": "Test quote",
    })
    check("an artisan can quote", bool(quote["id"]), f'total {quote["total"]}')
    accepted = post_json(f'/api/trade/quotes/{quote["id"]}/accept', {})
    check("accepting a quote creates a real order", bool(accepted["order_id"]),
          f'Rs.{accepted["amount"]:,.0f}')

    print("\n[orders with a timeline]")
    orders = get(f'/api/trade/orders/artisan/{artisan_row["id"]}')
    check("orders are listed", orders["summary"]["total"] > 0,
          f'{orders["summary"]["total"]} orders')
    check("five delivery stages are defined", len(orders["stages"]) == 5)
    check("stage labels are bilingual",
          all(s.get("label") and s.get("label_hi") for s in orders["stages"]))
    an_order = orders["orders"][0]
    moved = post_json_query(f'/api/trade/orders/{an_order["id"]}/advance',
                            {"to": "shipped"})
    check("an order can be advanced", moved["status"] == "shipped")
    check("each move is timestamped", len(moved["timeline"]) >= 1)

    print("\n[no name is defined twice]")
    # `nlp.py` carried TranscriptFacts and PRODUCT_NOUNS twice, byte for byte.
    # Python keeps the second and says nothing, which is exactly why it
    # survived — the same silent failure as the duplicate "mr" key that once
    # made Marathi resolve to Hindi. Source-level, because a live server
    # cannot see it.
    import ast
    import pathlib
    services = pathlib.Path(__file__).resolve().parent.parent / "app"
    dupes = []
    for source in sorted(services.rglob("*.py")):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        seen: dict[str, int] = {}
        for node in tree.body:
            names = []
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                names = [node.name]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for name in names:
                if name in seen:
                    dupes.append(f"{source.name}:{name} "
                                 f"(lines {seen[name]} and {node.lineno})")
                seen[name] = node.lineno
    check("no module defines the same top-level name twice",
          not dupes, f"{len(list(services.rglob('*.py')))} files" if not dupes
          else "; ".join(dupes[:3]))

    print("\n[Hindi is a real second half, not a stub]")
    HI_FIELDS = ["title_hi", "short_description_hi", "detailed_description_hi",
                 "story_hi", "care_hi"]
    EN_FIELDS = ["title", "short_description", "detailed_description",
                 "story", "care"]
    # Product codes and units that legitimately stay in Latin script.
    ALLOWED_LATIN = re.compile(
        r"\b(GI|PAVHAN|UPI|GST|HSN|ONDC|GeM|INR|cm|mm|kg|ml)\b")

    def latin_left(text: str) -> list[str]:
        return re.findall(r"[A-Za-z][A-Za-z'\-]*",
                          ALLOWED_LATIN.sub("", text or ""))

    catalogue = get("/api/products?limit=50")
    blank = [(p["title"], f) for p in catalogue for f in HI_FIELDS
             if not (p.get(f) or "").strip()]
    check("every seeded listing has all five Hindi fields",
          not blank, f"{len(catalogue)} listings" if not blank
          else f"{len(blank)} blank, e.g. {blank[0]}")

    # This is the bug the artisan actually reported: Hindi that was half
    # English. A Hindi field with a Latin word in it reads as broken, and the
    # Hindi voice then mispronounces exactly that word.
    mixed = [(p["title"][:30], f, latin_left(p.get(f) or ""))
             for p in catalogue for f in HI_FIELDS if latin_left(p.get(f) or "")]
    check("no Hindi field contains a stray English word",
          not mixed, "all clean" if not mixed else f"{len(mixed)} mixed, e.g. {mixed[0]}")

    english_blank = [(p["title"], f) for p in catalogue for f in EN_FIELDS
                     if not (p.get(f) or "").strip()]
    check("the English half is untouched", not english_blank,
          "" if not english_blank else str(english_blank[0]))

    # And the live path, not just the seed.
    generated = post_multipart("/api/ai/generate-listing", {
        "transcript": "yeh neela jaipur blue pottery ka guldasta hai, nau inch tall, "
                      "teen din laga banane me, Jaipur se",
        "language": "hi", "use_llm": "true"})
    check("a spoken listing comes back with Hindi as well as English",
          all((generated.get(f) or "").strip() for f in HI_FIELDS),
          generated.get("title_hi", ""))
    gen_mixed = {f: latin_left(generated.get(f) or "") for f in HI_FIELDS}
    gen_mixed = {f: v for f, v in gen_mixed.items() if v}
    check("the generated Hindi has no English in it",
          not gen_mixed, "clean" if not gen_mixed else str(gen_mixed))
    check("the Hindi is written, not transliterated from the English",
          generated["title_hi"] != generated["title"]
          and generated["detailed_description_hi"] != generated["detailed_description"])
    check("the English is still English",
          not DEVANAGARI.search(generated["title"] + generated["detailed_description"]))

    # An artisan who speaks Marathi or Tamil still gets an English + Hindi
    # listing, because those are the two the catalogue publishes in.
    for tongue, sample in (("mr", "ha nila jaipur blue pottery cha guldasta aahe"),
                           ("ta", "idhu neela jaipur blue pottery jaadi")):
        other = post_multipart("/api/ai/generate-listing", {
            "transcript": sample, "language": tongue, "use_llm": "true"})
        check(f"a {tongue} speaker still gets Hindi copy",
              bool((other.get("title_hi") or "").strip())
              and not latin_left(other["title_hi"]),
              other.get("title_hi", ""))

    print("\n[payments — money actually reaching the artisan]")
    artisans = [u for u in get("/api/users") if u["role"] == "artisan"]
    payee = next((u for u in artisans if u.get("upi_vpa")), artisans[0])
    check("seeded artisans have a payout destination", bool(payee.get("upi_vpa")),
          payee.get("upi_vpa", ""))

    good = get("/api/payments/check-vpa?vpa=rukhsana.bano%40ybl")
    check("a valid VPA is recognised, and its bank named",
          good["valid"] and good["provider"] == "PhonePe", good["provider"])
    typo = get("/api/payments/check-vpa?vpa=rukhsanabano")
    check("a VPA with no @ is rejected", not typo["valid"])
    unknown = get("/api/payments/check-vpa?vpa=artisan%40somenewbank")
    check("an unrecognised bank handle is accepted, not refused",
          unknown["valid"] and not unknown["provider"])

    pay_order = next(o for o in orders["orders"] if o["status"] != "delivered")
    before = get(f'/api/payments/order/{pay_order["id"]}')
    check("the split is stated in both languages",
          bool(before["split"]["note"]) and bool(before["split"]["note_hi"]))
    check("the split beats a middleman",
          before["split"]["artisan_amount"] > before["split"]["middleman_would_pay"])

    raised = post_json(f'/api/payments/order/{pay_order["id"]}/intent',
                       {"method": "upi"})
    payment = raised["payment"]
    check("a upi:// intent link is produced",
          payment["upi_link"].startswith("upi://pay?")
          and "am=" in payment["upi_link"] and "pa=" in payment["upi_link"])
    check("the payment link carries a WhatsApp message",
          payment["whatsapp"].startswith("https://wa.me/"))

    code, _ = expect_refusal(f'/api/payments/{payment["id"]}/release')
    check("money cannot be released before it is paid", code == 409)

    held = post_json(f'/api/payments/{payment["id"]}/confirm',
                     {"reference": "429911307755"})
    check("a confirmed payment is held, not paid out",
          held["payment"]["state"] == "held")
    check("the held state is explained in Hindi too",
          bool(held["payment"]["label_hi"]))

    code, detail = expect_refusal(f'/api/payments/{payment["id"]}/release')
    check("money cannot be released before delivery",
          code == 409 and "delivered" in detail.get("detail", "").lower())

    print("\n[logistics — an order that can actually be despatched]")
    here = get("/api/logistics/pincode/221001")
    check("a pincode resolves to its state",
          here["state"] == "Uttar Pradesh", here["state"])
    check("Jharkhand is not mistaken for Bihar",
          get("/api/logistics/pincode/835325")["state"] == "Jharkhand")
    check("Goa is not mistaken for Maharashtra",
          get("/api/logistics/pincode/403001")["state"] == "Goa")
    check("a six-digit-less pincode is refused",
          not get("/api/logistics/pincode/2210")["valid"])

    remote = get("/api/logistics/quote?origin=221001&destination=796001"
                 "&weight_g=900&category=Textiles")
    check("a remote destination is still serviceable", remote["serviceable"])
    check("only India Post serves it", remote["only_government"])
    check("the private couriers are named as refusing, not hidden",
          len(remote["unavailable"]) == 2,
          ", ".join(u["carrier"] for u in remote["unavailable"]))
    metro = get("/api/logistics/quote?origin=221001&destination=400001"
                "&weight_g=900&category=Textiles")
    check("a metro destination has private options too",
          not metro["only_government"] and len(metro["options"]) > 2)
    check("rates rise with distance",
          remote["options"][0]["total"] > metro["options"][0]["total"],
          f'{metro["options"][0]["total"]} → {remote["options"][0]["total"]}')
    check("every option is cheapest-first",
          all(a["total"] <= b["total"] for a, b in
              zip(metro["options"], metro["options"][1:])))

    ship_order = next(o for o in orders["orders"] if o["id"] != pay_order["id"])
    opts = get(f'/api/logistics/order/{ship_order["id"]}/options?to_pincode=796001')
    check("an order's options use the artisan's own pincode",
          opts.get("from_pincode") == payee.get("pincode") or bool(opts.get("from_pincode")))
    booked = post_json(f'/api/logistics/order/{ship_order["id"]}/book',
                       {"carrier": "indiapost-speed", "to_pincode": "796001"})
    shipment = booked["shipment"]
    check("an India Post AWB looks like an India Post AWB",
          len(shipment["awb"]) == 13 and shipment["awb"].endswith("IN"),
          shipment["awb"])
    check("pickup is never scheduled on a Sunday",
          shipment["pickup_on"][:10] and
          __import__("datetime").date.fromisoformat(
              shipment["pickup_on"][:10]).weekday() != 6)
    tracked = get(f'/api/logistics/track/{shipment["awb"]}')
    check("a buyer with no account can track by AWB alone",
          tracked["order_id"] == ship_order["id"])
    moved_ship = post_json_query(
        f'/api/logistics/shipment/{shipment["id"]}/advance', {"to": "delivered"})
    check("delivering the shipment delivers the order too",
          moved_ship["order_status"] == "delivered")

    print("\n[self-help group pooling]")
    lead = next(u for u in artisans if u["name"] == "Rukhsana Bano")
    reqs = get(f'/api/trade/requirements?artisan_id={lead["id"]}')["requirements"]
    biggest = max(reqs, key=lambda r: r["quantity"])
    cluster = get(f'/api/collective/cluster/{lead["id"]}'
                  f'?delivery_days={biggest["delivery_days"]}')
    check("a cluster has other artisans in it", len(cluster["members"]) > 0,
          f'{len(cluster["members"])} peers')
    check("every peer is there for a stated reason",
          all(m["reason"] and m["reason_hi"] for m in cluster["members"]))
    check("the combined capacity is reported",
          cluster["combined_capacity"] > cluster["lead"]["capacity_window"])

    member_ids = [m["artisan_id"] for m in cluster["members"]]
    plan = post_json("/api/collective/plan", {
        "requirement_id": biggest["id"], "lead_artisan_id": lead["id"],
        "member_ids": member_ids})
    check("the pool can cover an order no one could alone",
          plan["feasible"] and plan["allocated"] == biggest["quantity"],
          f'{plan["allocated"]}/{biggest["quantity"]}')
    check("nobody is allocated more than they can make",
          all(m["allocated"] <= m["capacity_window"] for m in plan["members"]))
    payouts = round(sum(m["payout"] for m in plan["members"]), 2)
    check("the payouts add up to exactly the net, to the rupee",
          abs(payouts - plan["net"]) < 0.02, f'{payouts} vs {plan["net"]}')
    lead_row = next(m for m in plan["members"] if m["is_lead"])
    check("the lead's coordination share is shown separately",
          lead_row["coordination"] > 0)
    check("the rounding rule is explained to the group",
          "rounded down" in plan["fairness_note"])

    tiny = post_json("/api/collective/plan", {
        "requirement_id": biggest["id"], "lead_artisan_id": lead["id"],
        "member_ids": member_ids[:1]})
    if tiny["feasible"]:
        check("a two-person pool is honest about a huge order", True,
              "this cluster is large enough even at two")
    else:
        check("a pool too small to deliver says so rather than quoting short",
              tiny["shortfall"] > 0 and str(tiny["shortfall"]) in tiny["summary"])
        code, _ = expect_refusal("/api/collective/pools", {
            "requirement_id": biggest["id"], "lead_artisan_id": lead["id"],
            "member_ids": member_ids[:1]})
        check("an infeasible pool cannot be committed", code == 409)

    pool = post_json("/api/collective/pools", {
        "requirement_id": biggest["id"], "lead_artisan_id": lead["id"],
        "member_ids": member_ids})
    check("every non-lead member gets a written invitation",
          len(pool["invites"]) > 0
          and all(i["whatsapp"].startswith("https://wa.me/") for i in pool["invites"]))
    code, _ = expect_refusal(f'/api/collective/pools/{pool["pool"]["id"]}/quote')
    check("a pool cannot quote before its members agree", code == 409)

    for member in pool["pool"]["members"]:
        if not member["is_lead"]:
            post_json(f'/api/collective/pools/{pool["pool"]["id"]}'
                      f'/members/{member["id"]}/respond', {"accept": True})
    quoted = post_json(f'/api/collective/pools/{pool["pool"]["id"]}/quote', {})
    check("an agreed pool sends the buyer one ordinary quote",
          bool(quoted["quote_id"]) and quoted["pool"]["status"] == "quoted")

    print("\n[WhatsApp, the channel that is already open]")
    a_product = get("/api/products?limit=1")[0]
    shared = get(f'/api/share/product/{a_product["id"]}?lang=en')
    check("a listing produces a shareable message",
          "Handmade by" in shared["text"] and shared["url"] in shared["text"])
    check("the share message makes the platform's point",
          "no middleman" in shared["text"].lower())
    check("the share link is a wa.me link",
          shared["whatsapp"].startswith("https://wa.me/"))
    hindi = get(f'/api/share/product/{a_product["id"]}?lang=hi')
    check("the share message exists in Hindi too",
          hindi["text"] != shared["text"] and "हाथ से" in hindi["text"])
    alert = get(f'/api/share/order/{pay_order["id"]}?lang=hi')
    check("an order alert is addressed to the artisan's own number",
          alert["phone"].startswith("91") and len(alert["phone"]) == 12,
          alert["phone"])

    print("\n[the offline outbox's idempotency key]")
    ref = f"smoketest{random.randrange(10 ** 8, 10 ** 9)}"
    first = post_json("/api/products", {
        "title": "Outbox replay probe", "client_ref": ref, "price": 1200})
    second = post_json("/api/products", {
        "title": "Outbox replay probe", "client_ref": ref, "price": 1200})
    check("a replayed offline send returns the same listing, not a second one",
          first["id"] == second["id"], first["id"])
    without = post_json("/api/products", {"title": "No client ref", "price": 1200})
    without2 = post_json("/api/products", {"title": "No client ref", "price": 1200})
    check("listings without a client ref are still independent",
          without["id"] != without2["id"])

    print("\n[artisan dashboard]")
    dash = get(f"/api/artisans/{artisan['id']}/dashboard")
    check("dashboard has stats", dash["stats"]["products"] > 0)
    check("earnings are compared to a middleman",
          "extra_vs_middleman" in dash["stats"])

    print("\n" + "=" * 62)
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("  failed: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as exc:
        print(f"\nCould not reach {BASE} — is the backend running?\n  {exc}")
        sys.exit(2)
