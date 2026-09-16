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
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("PAVHAN_URL", "http://127.0.0.1:8000").rstrip("/")

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
    otp = post_json("/api/auth/request-otp", {"phone": "9990001111"})
    check("OTP requested", otp["sent"])
    check("demo code is exposed only because no SMS gateway is set",
          bool(otp["demo_code"]) and otp["delivered_by_sms"] is False)
    session = post_json("/api/auth/verify-otp", {
        "phone": "9990001111", "code": otp["demo_code"], "name": "Test Artisan",
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
