# PAVHAN — AI-Powered Growth for Artisan Craft

**Smart India Hackathon · Problem Statement 26090**

An Indian artisan can make a Banarasi saree worth ₹35,000 and be paid ₹14,000 for
it at the door, because the person who knows what it is worth is never the person
who made it. PAVHAN closes that gap with one interaction the artisan already knows
how to do: **take a photo and talk.**

From a photograph and a spoken sentence in Hindi, PAVHAN produces a complete
catalogue listing, a defensible price with the arithmetic shown line by line, and
a ranked list of real buyers with a message already written to each one.

---

## What it actually does

| Step | What the artisan does | What PAVHAN does |
|---|---|---|
| 1 | Photographs the piece | Reads colour, texture, intricacy and symmetry from the pixels; scores the photo and coaches them if it is dark, blurred or cluttered |
| 2 | Speaks in Hindi, Hinglish or English | Extracts material, colour, size, weight, days of work, origin and care from the actual sentence — and asks for what is missing |
| 3 | Checks the draft | A written listing, story, tags and SEO keywords — nothing invented that was not said or seen |
| 4 | Sees the price | Floor / recommended / premium, with a breakdown they can show to any buyer, plus what a middleman, a bazaar stall, a boutique and an export house would each pay |
| 5 | Picks buyers | 12 buyer profiles scored on 7 weighted signals, each explaining itself, with quantity, unit price and a ready pitch |

A voice guide speaks every screen out loud, in Hindi, from the first second the
app opens — because an artisan listing a product for the first time needs
somebody talking them through it, not a tooltip.

---

## Running it

```bash
git clone https://github.com/deepakvish001/sih26060.git
cd sih26060
./run.sh                 # macOS / Linux / Git Bash
```

On Windows, double-click **`run.bat`** (or run it from Command Prompt).

Either one installs what it needs on the first run, builds the app, and then
prints:

```
    App   →  http://localhost:8000
    API   →  http://localhost:8000/docs
```

One process, one port, everything served together. Open it in **Chrome or
Edge**.

> ### Use the `localhost` address exactly as printed
>
> Browsers switch the microphone **off** on any address that is neither
> `localhost` nor `https://`. If you open the app through your machine's LAN
> address (`http://192.168.x.x:8000`) the mic will be dead and Chrome will not
> tell you why — it fails silently. This is the single most common reason a
> voice feature looks broken.
>
> PAVHAN detects this and says so: the Speak screen carries a diagnostics panel
> that reports the exact blocker (insecure address, denied permission, no input
> device, unsupported browser) and what to do about it. Tap it to see the full
> readout.
>
> To demo from a phone, either run it on the phone itself, or put it behind
> HTTPS (a tunnel such as `ngrok http 8000` is enough) — the mic then works.

Other modes:

```bash
./run.sh dev        # two ports with hot reload: API :8000, app :5173
./run.sh backend    # API only
./run.sh test       # 42-check API smoke test against a running server
```

### Optional: connect Claude

Everything above works with **no API key at all** — the on-device engines are the
default path, not a stub. Add a key and the copywriting and image understanding
route through Claude instead, with the extracted facts still enforced:

```bash
cp backend/.env.example backend/.env
# then set ANTHROPIC_API_KEY=sk-ant-...
```

The app header and Profile screen always show which engines are live.

---

## Architecture

```
┌──────────────── React 18 + Vite (mobile-first, 460px shell) ────────────────┐
│  Welcome / role picker ──▶ artisan · shopper · bulk buyer · exporter        │
│  Voice cataloguer: photo → speak → review → price → buyers → live          │
│  Marketplace · search · product detail · B2B sourcing · dashboard          │
│  useSpeechRecognition  (mic, level meter, auto-restart, mapped errors)      │
│  useVoiceAssistant     (Hindi TTS, voice selection, autoplay unlock)        │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │ REST / JSON
┌────────────────────────────────▼───────────────────────────────────────────┐
│                    FastAPI + SQLAlchemy + SQLite                            │
│                                                                             │
│  services/vision.py      colour science, edge density, symmetry, entropy    │
│  services/nlp.py         Hindi + Hinglish + English fact extraction         │
│  services/taxonomy.py    18 crafts: economics, GI status, visual signature  │
│  services/listing.py     3-stream craft inference with confidence + evidence│
│  services/pricing.py     explainable cost-plus-market pricing               │
│  services/matching.py    7-signal buyer scoring with per-factor reasons     │
│  services/search_engine.py  BM25 + bilingual synonyms + fuzzy + facets      │
│  services/voice_scripts.py  per-screen guide copy, Hindi and English        │
│  services/llm.py         optional Claude layer, fails back silently         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How the craft is actually identified

Three independent evidence streams are combined, so changing the photo *or* the
words changes the answer:

| Signal | Weight | Source |
|---|---|---|
| Keyword evidence | 0.60 | craft vocabulary in Hindi, Hinglish and Devanagari |
| Colour affinity | 0.22 | quantised palette from the photograph |
| Silhouette + surface | 0.18 | aspect ratio, symmetry, edge density, entropy |
| Material named | +0.35 | corroboration bonus |
| Region named | +0.30 | corroboration bonus |

The result carries a confidence score and the evidence in plain language
("you said words specific to Jaipur Blue Pottery", "the photo's blue and white
palette matches this craft"). Below ~55% confidence PAVHAN says it is unsure and
asks the artisan to confirm, rather than guessing with a straight face.

### How the price is built

```
material                       market rate for the craft and unit
+ labour        hours × honest hourly wage for the skill band × measured intricacy
+ cluster premium              Varanasi, Srinagar, Bidar etc. command more
+ GI authenticity              12% for Geographical Indication protected craft
+ natural dye                  7% where the artisan says no chemicals were used
+ packaging                    craft-appropriate protective packing
± listing quality              completeness of the listing itself
× seasonal demand index        Diwali 1.18 · monsoon 0.92 · wedding season 1.14
× channel margin               direct 10% · marketplace 22% · B2B 8% · export 34%
```

Hourly wages start at ₹55 for an apprentice and reach ₹180 for a heritage-craft
master — deliberately above the piece rate an artisan is usually offered. The
screen then states the effective hourly wage they end up with, and warns them
when it is still under ₹60/hour.

### How buyers are matched

Every buyer is scored against **that specific product** on seven weighted
signals — category fit (0.26), price band (0.22), order capacity (0.16),
material (0.12), sourcing region (0.10), values and certification (0.09), and
buyer reliability (0.05) — and each factor returns its own explanation. A bamboo
basket surfaces Fabindia, Anthropologie and the Nordic collective; a Banarasi
saree surfaces a Paris export house and a Jaipur bridal boutique. The screen also
names the gaps ("your 14-day lead time exceeds their 10-day limit") so the
artisan knows what to fix.

---

## Everything is bilingual, including the reasoning

This is not a UI string table. The pricing breakdown notes, the market season
labels, the comparables, the buyer match explanations, the photo coaching and the
gaps all exist in Hindi and English, because an explanation an artisan cannot
read is not an explanation. Hindi number words are parsed too — `बारह दिन`,
`saade paanch metre` and `chaar sau gram` all resolve correctly.

---

## Seed data

The app never opens onto an empty screen: 6 artisans across 6 clusters, 16
listings spanning all 7 craft categories, 12 B2B buyer profiles with genuinely
different sourcing rules, and sales history so the dashboard has something to
say. Seed prices come from the same pricing engine the live flow uses.

Reset the demo catalogue at any time: `POST /api/admin/reseed`.

---

## API

Full interactive documentation at `/docs`. The endpoints that matter:

| Endpoint | Purpose |
|---|---|
| `POST /api/ai/analyze-image` | Colour, texture, intricacy and photo coaching |
| `POST /api/ai/generate-listing` | Photo + voice → complete priced listing |
| `POST /api/ai/coach` | Live "what have you not told me yet" while speaking |
| `POST /api/ai/transcribe` | Server-side speech-to-text fallback |
| `GET /api/search` | BM25 + synonyms + fuzzy + facets, Hindi or English |
| `GET /api/search/suggest` | Prefix autocomplete |
| `POST /api/pricing/recommend` | Explainable price band |
| `GET /api/pricing/product/{id}` | "Is my price still right?" re-check |
| `GET /api/pricing/market-context` | Season curve and channel margins |
| `GET /api/buyers/match/{product_id}` | Scored buyers for one product |
| `GET /api/buyers/{id}/recommended-products` | The mirror, for the B2B side |
| `GET /api/voice/scripts` | Every screen's guide copy |
| `GET /api/artisans/{id}/dashboard` | Earnings, pipeline, uplift vs middleman |

---

## Tests

```bash
./run.sh test
```

42 checks covering the claims this project actually makes: two different photos
must read differently, two different voice notes must produce different crafts
and different prices, a Hindi query and an English query must find the same
listing, every engine explanation must exist in both languages, and different
products must match different buyers.

---

## Tech

React 18 · Vite 5 · React Router 6 · FastAPI · SQLAlchemy 2 · Pydantic 2 ·
Pillow · SQLite · Web Speech API · optional Claude API

No CSS framework and no component library — the interface is built from a small
design system in `frontend/src/styles/theme.css` drawn from the crafts
themselves: indigo dye, marigold, madder red and unbleached cotton.
