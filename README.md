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
| 1 | Photographs the piece | **AI Product Studio**: removes the cluttered background, corrects the colour cast and exposure, sharpens the detail and crops to a 1600×1600 e-commerce master — with a real before/after |
| 2 | Speaks in **any of 12 Indian languages** | Extracts material, colour, size, weight, days of work, origin and care from the actual sentence — and asks for what is missing. The listing always comes out in English **and** Hindi |
| 3 | Checks the draft | A written listing, story, tags and SEO keywords — nothing invented that was not said or seen |
| 4 | Sees the price, and enters what they spent | **Two engines side by side**: a cost-plus calculation they can show to any buyer, and a trained gradient-boosting model that says what the market pays for pieces like this — each explaining itself, and the disagreement between them reported rather than averaged away |
| 5 | Picks buyers | 12 buyer profiles scored on 7 weighted signals, each explaining itself, with quantity, unit price and a ready pitch |
| 6 | Sends it to a government portal | GeM and ONDC packages with HSN classification and the statutory declarations already filled, plus a readiness check naming anything still missing |
| 7 | Stands at a physical fair | **Fair mode**: a printable QR for the stall that turns a walk-past visitor into a follower and a repeat customer after the fair has packed up |
| 8 | Answers a bulk enquiry | Buyer requirements ranked against *their* catalogue, a quote sheet with the margin shown, and an accepted quote that becomes a tracked order |
| 9 | Proves it worked | A scheme-linked impact record the artisan owns, and a ministry-level report that aggregates it without ever inventing a number |

A voice guide speaks every screen out loud, in Hindi, from the first second the
app opens — because an artisan listing a product for the first time needs
somebody talking them through it, not a tooltip.

---

## Running it

```bash
git clone https://github.com/deepakvish001/PAVHAN.git
cd PAVHAN
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
Edge**, and use the install prompt in Profile to put it on the home screen —
it then opens without an internet connection and keeps showing the artisan's
saved work.

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
./run.sh test       # 118-check API smoke test against a running server
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
│  Requirements → quote → order book · fair mode + stall storefront          │
│  Impact: the artisan's own record, and the ministry's aggregate            │
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
│  services/schemes.py     MoSJE corporations, schemes, instalment arithmetic  │
│  services/impact.py      measured uplift, with implausible rows excluded    │
│  services/fairs.py       stall codes, printable QR, post-fair attribution   │
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

### What the AI Product Studio actually does

The problem statement names this feature first, and it runs entirely on the
device — OpenCV only, no model download, no API key, no network:

1. **Segment the product.** A background colour model is clustered from the
   border (a room is a wall *and* a floor, not one colour), combined with a
   centre prior and an edge map, and used to seed GrabCut. The mask is then
   cleaned, hole-filled and feathered.
2. **Correct the colour — measured on the product, not the room.** A photo of
   a tan basket against a brown wall is mostly wall, so correcting against the
   whole frame drains the basket along with the wall. Segmentation therefore
   runs *before* white balance and exposure.
3. **Lift the light.** Shades-of-grey white balance, a gamma lift to a studio
   brightness, CLAHE for local contrast, and unsharp masking for the weave.
4. **Compose and frame.** White, studio gradient with a contact shadow, or a
   transparent PNG; then cropped to the product, squared and resized to 1600px.

It refuses when it should. Two signals have to agree before a cut-out is
trusted: the kept and discarded regions must differ in Lab, **and** they must
differ by more than the picture differs from itself. A product that already
fills the frame, or one shot against a cloth of its own shade, is left alone
with an explanation — "shoot against a plain white cloth" — instead of being
silently mangled.

### The twelve languages

An artisan speaks; the listing comes out in English and Hindi. Input is
accepted in **Hindi, English, Marathi, Bengali, Assamese, Tamil, Telugu,
Kannada, Malayalam, Gujarati, Punjabi and Odia**, in either the native script
or romanised.

Detection reads the Unicode block first, which is unambiguous — Tamil text can
only be Tamil. Where a script carries two languages (Devanagari holds Hindi and
Marathi; Bengali holds Bengali and Assamese) a small set of everyday marker
words separates them, and the language the artisan picked in the app settles
anything still ambiguous.

The language is also evidence about the craft. "Silk saree" spoken in Tamil
means Kanjeevaram, not Banarasi, and `LANGUAGE_AFFINITY` encodes that — which
is why the taxonomy now carries Kanjeevaram, Pochampally, Bandhani,
Sambalpuri, Muga and Kasuti alongside the northern crafts.

### The pricing model

The problem statement asks for a machine-learning algorithm, and there is one:
a `GradientBoostingRegressor` trained on log-price, scoring **R² 0.979 with a
median error of 8.2%** and 89% of held-out pieces within 20%.

There is no public dataset of what Indian artisan craft actually sells for —
that information asymmetry is the problem this project exists to fix. So the
model is trained on a simulated market whose data-generating process is written
down in full in `app/ml/dataset.py` rather than scraped from somewhere
unverifiable. The simulation deliberately contains effects the rules engine
does **not** model, and those are what the model has to learn: diminishing
returns on labour, category-specific price elasticity, an interaction between
GI status and export demand, threshold effects on listing quality, and seasons
that peak differently by category.

Both engines are shown to the artisan, because they answer different questions:

* the **cost-plus engine** answers *"what is this worth, and here is the
  arithmetic"* — which is what you show a trader at your door;
* the **model** answers *"what does this market pay for pieces like this"* —
  which is what makes a listing sell.

When they disagree by more than 18% that is reported, not averaged away: a wide
gap usually means an unusual input, and the recommendation stays anchored to
the artisan's costs so they cannot end up below them. Each model prediction
also carries a **local** explanation — every feature is pushed back to a
typical value and the model re-queried, so "GI certification +₹6,714" is
measured for that specific piece rather than read off a global chart.

Retrain at any time with `python -m app.ml.train`.

### Government e-marketplaces

`/api/export/{id}` produces a submission-shaped package for **GeM** and
**ONDC**: correct HSN classification (the commonest reason an artisan listing
is rejected, and not something they can reasonably be expected to know), the
Legal Metrology statutory declarations, country-of-origin, and a readiness
report naming every field a portal would bounce it for.

What it does **not** do is claim an integration that does not exist. The final
push needs a registered seller account and API credentials, which are granted
to an organisation rather than issued to an application — and the app says so
on the screen. Everything up to that point, which is the part an artisan could
never do alone, is done.

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

### From "which buyers suit this?" to an actual order

Buyer matching answers a question the artisan can only ask *after* they have
made something. The other direction was missing, so it is here now: a buyer
posts a requirement — 400 jute bags, ₹180–₹260, 45 days, Bengal or Assam — and
every artisan sees it **ranked against their own catalogue**, with the ranking
explaining itself the same way the buyer matcher does.

The artisan answers with a quote. The quote sheet does the arithmetic out loud:
unit price × quantity, minus the cost the pricing engine already knows, leaving
the margin — so nobody accepts a large order at a loss because the number
looked big. An accepted quote is not a notification; it creates a real **order**
that moves through five stages (placed → accepted → in production → shipped →
delivered), each stamped and each labelled in Hindi and English. Those orders
are the same rows the impact report later counts, which is why the impact
figures are transaction-derived rather than declared.

### Fair mode: keeping the customer after the stall comes down

The problem statement's own words: exhibitions give "a temporary boost in
sales", and what artisans lack is "continuous, year-round access". A visitor
who admires a piece at Surajkund has no way to find that weaver again in March.
The relationship ends when the stall is dismantled.

So an artisan joining a fair (Shilp Samagam, Surajkund, Dilli Haat, IITF,
Hunar Haat, or one they type in themselves) gets a **printable stall QR** — an
SVG, so it stays sharp on an A4 sheet taped to a stall frame, with high error
correction because that sheet will be creased and half-covered. Scanning it
opens that artisan's storefront and offers one button: follow.

The stall page then reports the only number that matters to a ministry funding
those stalls: how many scans, how many follows, and **how much of the resulting
sales landed after the fair had closed**. A fair that produced ₹40,000 during
the week and nothing afterwards, and one that produced ₹40,000 during the week
and ₹1,20,000 over the next three months, are not the same fair — and until
now nobody could tell them apart.

### The MoSJE evidence layer

The Ministry disburses money through NSFDC, NSKFDC, NBCFDC, NDFDC and the DNT
board — PM-DAKSH, PM-AJAY, SCA-SCSP, VCF-SC — and then has almost no way to
learn what happened to that household's income. What evaluation exists is a
survey: recalled figures, years later, from people with a reason to answer a
particular way.

PAVHAN holds the artisan's actual transactions, so it can answer that question
with arithmetic. An artisan links their corporation, scheme, beneficiary ID,
social category and loan, and the report shows monthly earnings, uplift against
their own stated baseline, the counterfactual of selling at a trader's door,
and whether the earnings cover the loan instalment. The ministry view
aggregates the same rows by corporation and by social category.

Three rules keep it honest, and they are the reason the numbers are believable:

* **The baseline is labelled self-declared**, everywhere it is used. The
  artisan states what they earned before; PAVHAN never presents that as
  verified.
* **Tenure comes from the earliest evidence**, not the account's creation date.
  Dividing a year of sales by a two-week-old account produced monthly earnings
  of lakhs and an uplift of 2,600% — a number that would have destroyed the
  report's credibility in front of a panel. The start date is now the earliest
  of the account, its first listing and its first order.
* **An uplift above 400% is excluded** from the published average as a
  mis-stated baseline rather than a result — and excluded from the
  per-corporation breakdown too, so the headline and the breakdown cannot
  contradict each other. The report says how many rows it excluded and what
  sample the mean rests on.

Artisans with **negative** outcomes stay in the table. A report that only ever
shows success is not evidence.

PAVHAN does not lend or recover money, and the screen says so.

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

## Built for the person who actually has to use it

The intended user may be sixty, may not read comfortably, and may be holding
the phone at arm's length in bright sunlight. So:

* **Text size is adjustable in the app** — one `--font-scale` on the root that
  every declared size multiplies itself by, so 145% enlarges the *whole*
  interface (buttons, labels, navigation, not just body copy) without breaking
  the layout or introducing a horizontal scrollbar.
* **A high-contrast palette** switches the entire theme, not just the body text.
* **Every interactive target is at least 44px**, the size a thumb can actually
  hit.
* **Keyboard and screen-reader paths work**: a skip link, visible
  `:focus-visible` rings, labelled controls, and live regions where the app
  speaks.
* The preferences persist, because an artisan should not have to set them again
  every time they open the app.

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
| `POST /api/studio/enhance` | Phone snapshot → e-commerce product photo, with a before/after and a report |
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
| `POST /api/assistant/ask` | Free-form question → answer grounded in this artisan's data |
| `POST /api/auth/request-otp` · `verify-otp` | Mobile sign-in |
| `GET /api/voice/scripts` | Every screen's guide copy |
| `GET /api/voice/labels` | Hindi names for craft types, categories, materials, regions |
| `GET /api/voice/languages` | The 12 input languages, with speech and TTS locales |
| `GET /api/pricing/model` | The model card: algorithm, measured accuracy, feature importance |
| `GET /api/export/{id}?format=gem\|ondc\|csv` | Government marketplace package |
| `GET /api/export/readiness/{id}` | What is still missing before submission |
| `GET /api/artisans/{id}/dashboard` | Earnings, pipeline, uplift vs middleman |
| `GET /api/trade/requirements?artisan_id=` | Buyer requirements ranked against this artisan's catalogue, with reasons |
| `POST /api/trade/requirements` | A buyer posts what they need |
| `POST /api/trade/quotes` | An artisan quotes against a requirement |
| `POST /api/trade/quotes/{id}/accept` | Accepted quote → a real order |
| `GET /api/trade/orders/artisan/{id}` | Order book with the five-stage timeline |
| `POST /api/trade/orders/{id}/advance?to=` | Move an order to its next stage |
| `GET /api/fairs` | The fairs an artisan can take a stall at |
| `POST /api/fairs/stall` | Join a fair and get a stall code |
| `GET /api/fairs/stall/{code}/qr.svg` | The printable stall QR |
| `GET /api/fairs/stall/{code}?follow=` | The visitor's storefront view, and the follow action |
| `GET /api/fairs/stall/{code}/performance` | Scans, follows, and sales *after* the fair closed |
| `GET /api/impact/schemes` | MoSJE corporations, schemes and social categories |
| `POST /api/impact/artisan/{id}/link` | Link a beneficiary to a scheme and loan |
| `GET /api/impact/artisan/{id}` | One artisan's measured outcome |
| `GET /api/impact/ministry` · `ministry.csv` | Aggregate report by corporation and social category |

---

## Tests

```bash
./run.sh test
```

118 checks covering the claims this project actually makes: two different photos
must read differently, two different voice notes must produce different crafts
and different prices, a Hindi query and an English query must find the same
listing, every engine explanation must exist in both languages, different
products must match different buyers, a quote that is accepted must produce a
real order, and an impact report must refuse to publish an uplift figure it
cannot stand behind.

The suite reseeds the catalogue before it starts and uses a fresh phone number
each run, so it passes twice in a row on the same server rather than tripping
over the state it created the first time.

---

## Tech

React 18 · Vite 5 · React Router 6 · FastAPI · SQLAlchemy 2 · Pydantic 2 ·
Pillow · OpenCV · NumPy · scikit-learn · SQLite · Web Speech API ·
service worker + web app manifest · optional Claude API

No CSS framework and no component library — the interface is built from a small
design system in `frontend/src/styles/theme.css` drawn from the crafts
themselves: indigo dye, marigold, madder red and unbleached cotton.
