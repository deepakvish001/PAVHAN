# PAVHAN — engineering notes

Notes on the decisions that are not obvious from reading the code.

## Why the AI runs on-device by default

A hackathon demo that dies when the venue Wi-Fi drops, or when an API key runs
out of credit, is not a demo. So every intelligent behaviour in PAVHAN has a real
local implementation, and the Claude API is a quality upgrade layered on top —
never a dependency.

That constraint turned out to be a design benefit. Because the local engines had
to be genuinely good, they are explainable in a way a single LLM call is not: the
pricing engine can show its arithmetic, the matching engine can show its per-
factor scores, and the craft identifier can show its evidence. An artisan
negotiating with a trader needs the arithmetic, not a confident sentence.

## The three things that had to be fixed first

The prototype this replaces failed in three specific ways, and the architecture
is shaped around not repeating them.

### 1. Every upload returned the same Banarasi saree

The fix is that craft identification is a *scored inference over three
independent evidence streams* (`services/listing.py:infer_craft`), not a lookup.
Keyword evidence from the transcript carries 0.60, palette affinity from the
photograph 0.22, and silhouette plus surface 0.18, with corroboration bonuses for
a named material or region. Change the photo and the score moves; change the
words and it moves more.

Below ~55% confidence the app declines to guess and asks the artisan to confirm.
Saying "I am not sure" is a feature — a confidently wrong craft type means the
listing never appears in the right search.

`tests/smoke_test.py` asserts this directly: two different photos must produce
different palettes, silhouettes and intricacy values, and two different voice
notes must produce different crafts, titles and prices.

### 2. The microphone did nothing

Four separate causes, all handled explicitly in
`frontend/src/hooks/useSpeechRecognition.js`:

- **Insecure context.** `getUserMedia` and the Web Speech API are disabled
  outside `https://` and `localhost`, silently. We detect it and say so.
- **The permission prompt never appeared.** Calling `recognition.start()` alone
  does not reliably raise it. We call `getUserMedia` first — which does — and
  keep the stream for a live input-level meter, so the artisan can *see* that
  the mic is hearing them. That visible feedback matters more than it sounds:
  without it, a user who is being heard perfectly still thinks it is broken.
- **Chrome ends the session after a few seconds of silence.** An artisan pauses
  to think, `onend` fires, and recording stops. We restart while the user still
  intends to be recording.
- **Every error was swallowed.** Each `SpeechRecognition` error code now maps to
  a sentence in the artisan's own language, with the next thing to try.

When speech recognition is genuinely unavailable, `MediaRecorder` plus server
transcription takes over, and typing always works. The app states which path is
active rather than appearing broken.

### 3. Buyer matching showed "select a product" and then nothing

`services/matching.py` scores every buyer against one concrete product on seven
weighted signals and returns a per-factor explanation for each. The screen
auto-selects the artisan's first product so it is never empty.

One subtlety worth recording: the first implementation averaged category overlap
across all of a product's tags, which buried exact matches — a buyer who
literally sources "Pottery & Ceramics" scored 0.2 on a pottery listing because
the product also carried nine tags they had never mentioned. `_category_fit`
now checks the primary category first and falls back to progressively weaker
evidence. Strong matches went from 0 to 6 on the same data.

## Two bugs that only showed up on someone else's laptop

**The steps were declared inside the page component.** `PhotoStep`, `VoiceStep`
and the rest lived inside `AddProduct`, so every parent render produced a new
component *type*, React unmounted the old one, and the step's state went with
it. Switching language halfway through the flow silently threw away the photo
and the transcript the artisan had just recorded. They are module-level
components now, and the flow's state lives in the parent. A React lesson worth
keeping: defining a component inside another component is never a cosmetic
choice.

**The voice guide talked over itself.** Picking a role greets the artisan and
navigates at the same time, and the screen it lands on immediately spoke its own
script — which calls `speechSynthesis.cancel()` first, cutting the greeting off
about a second in. The fix has two halves: a greeting started through
`sayProtected` holds the floor for roughly as long as it takes to read, and
screen scripts queue behind it instead of interrupting. The hold is released
early when the utterance genuinely ends, so nothing waits out an estimate.

Testing that second one needed a fake speech engine. Headless Chromium ships no
voices, so every utterance "ends" instantly and the overlap cannot be
reproduced; the regression test installs a `speechSynthesis` stub whose
utterances take a realistic reading time, which is the only way the bug is
visible outside a real laptop.

## Hindi is a first-class language, not a translation layer

Three things follow from taking this seriously:

**Extraction accepts all three scripts.** Artisans speak Hinglish — "Yeh
Banarasi silk saree hai, saade paanch metre" — mixing Devanagari, Roman Hindi
and English in one sentence. Every extractor in `services/nlp.py` accepts all
three, including number words: `बारह`, `barah` and `twelve` all resolve to 12,
`saade paanch` to 5.5, and `chaar sau gram` to 400g.

**Vocabulary matches are returned in sentence order.** In "red aur golden
design", red is the main colour and gold is the accent. Returning them in
dictionary order produced "Golden Red Banarasi Saree", which reads wrong to
anyone who knows the craft.

**The reasoning is translated, not just the labels.** The pricing breakdown
notes, season labels, comparables, match explanations, photo coaching and gap
warnings all carry a `_hi` variant. An explanation the artisan cannot read is
not an explanation.

**The data is translated too.** Translating the UI chrome while leaving
"Pottery & Ceramics · Varanasi · Pure Silk" in English produces a half-Hindi
screen that reads worse than either language alone. `taxonomy.label_pack()`
serves Hindi names for craft types, categories, materials, regions, colours,
techniques and buyer types; the app pulls them once per language change and
`L(value)` renders any API token in the current language, falling through
unchanged when there is no Hindi name. Product titles are deliberately left
alone — those are the artisan's own words, not ours to rewrite.

## Pricing for dignity, then for the market

The engine is deliberately cost-plus first and market-adjusted second, because
the failure it is fixing is an artisan accepting a piece rate that values their
time at ₹20/hour. Wages start at ₹55/hour for an apprentice and reach ₹180 for
heritage-craft masters, and the screen reports the effective hourly wage the
artisan actually ends up with — warning them when it is still under ₹60.

Two guards worth noting:

- The **floor** is cost + 4%. The engine will not recommend a loss.
- The seed catalogue uses *focused working days of six hours*, not elapsed
  calendar days. An early version treated a 21-day calendar span as 126 paid
  hours and priced a saree at ₹44,000. Anything that turns time into money has
  to be precise about which kind of time it means.

## Search

BM25 over a weighted field concatenation (title 4.0 … story 0.5), with a synonym
layer that collapses `साड़ी`, `saree`, `sari` and `sadi` into one concept before
anything is scored, and a `difflib` pass for typos. Coverage is folded into the
final score so a document matching every query term outranks one that matched a
single common term many times. Facets are computed from live data, so adding a
craft cluster needs no UI change.

## Training a model with no dataset to train on

The honest problem: nobody publishes what Indian artisan craft sells for. The
absence of that number is the whole reason a weaver accepts ₹14,000 for a
₹35,000 saree. So a scraped dataset was not an option, and inventing one
quietly would have been worse.

What `app/ml/dataset.py` does instead is write the market model down. Every
effect is stated and auditable: how labour saturates, how each category's
ceiling compresses the top end, how a GI tag is worth more where export demand
already exists, how presentation is a threshold rather than a slope, how
textiles and decor peak in different months. A reviewer can disagree with a
coefficient and change it; they cannot be misled about where the number came
from.

The important design constraint was that the simulation must **not** be the
rules engine with noise added. If it were, the model would only rediscover the
rules and add nothing. Every effect listed above is one the rules engine does
not express, which is why the two engines disagree on unusual inputs — and
that disagreement is information worth showing rather than a bug to smooth
over.

Training on `log1p(price)` rather than price matters more than it looks. Craft
prices span three orders of magnitude; optimising raw rupee error would let
the model ignore everything under a few thousand rupees, which is most of what
a bamboo weaver makes. In log space the model optimises proportional error,
which is what "10% off" means to the person being paid.

## Local explanations, not a global chart

Feature importance says the same thing for every product, which is useless to
the artisan looking at one piece. `pricing_ml._explain` pushes each feature
back to a typical value one at a time and re-queries the model, so the number
on screen — "GI certification +₹6,714" — is that feature's contribution for
*this* piece. It costs fourteen extra predictions and turns a model into an
explanation.

## Making a ministry statistic you could defend in a review meeting

The impact report was the first feature where being *wrong* was worse than
being absent. Its first run produced a mean uplift of **2,653%** and a monthly
income of ₹1.79 lakh for a rural artisan. Both were arithmetically correct and
completely fake, and a panel would have stopped reading there.

Three defects, all of the same shape — a number divided by the wrong
denominator:

1. **Tenure came from `User.created_at`.** Seeded and imported artisans are
   created *now* while their order history spans months, so a year of sales was
   being divided by a two-week-old account. Fixed by taking the earliest of the
   account, its first listing and its first order:

   ```python
   candidates = [_aware(artisan.created_at)]
   candidates += [_aware(p.created_at) for p in products]
   candidates += [_aware(o.created_at) for o in orders]
   started = min((c for c in candidates if c), default=now)
   ```

2. **A single mis-stated baseline dominated the mean.** An artisan who declares
   ₹300/month produces a four-figure uplift percentage that swamps every honest
   row. `IMPLAUSIBLE_UPLIFT = 400.0` excludes those from the published average,
   and the response reports `uplift_sample_size`,
   `uplift_excluded_implausible` and `uplift_excluded` so the exclusion is
   visible rather than quiet.

3. **The headline and the breakdown disagreed.** The exclusion was applied when
   computing the ministry headline but not when grouping by corporation, so the
   page showed a mean of +83.5% above a corporation row reading +486.2%. A
   report that contradicts itself on the same screen is worse than no report.
   The filter now runs once, before both.

Artisans with negative outcomes are kept in the table. The demo report shows
two (−3% and −60.1%) and that is the point: a tool that only ever reports
success is not measuring anything.

## Why a fair needs a QR and not a listing

Fair mode looks like a small feature and is the one that maps most directly
onto the problem statement's diagnosis — "a temporary boost in sales" versus
"continuous, year-round access". The mechanism is deliberately minimal: a code,
a printed square, a storefront, a follow button.

The QR is **SVG, not PNG**, because it is printed on A4 and taped to a stall
frame, and a raster QR scaled to the wrong size is a QR that will not scan. It
uses `ERROR_CORRECT_H` because that sheet will be creased and partly obscured
by whatever is hanging in front of it. Dark modules are emitted as run-length
`<rect>` runs rather than one per module, which keeps the SVG small enough to
inline in a JSON response. Stall codes omit `0`/`O` and `1`/`I`/`L`, because
sometimes a visitor types the code by hand when a camera will not focus.

The measurement is the reason the feature exists: `stall/{code}/performance`
splits sales into during-fair and after-fair. Two fairs with identical takings
on the day are not the same fair, and nothing before this could tell them
apart.

## Requirements, quotes and orders share the pricing engine's numbers

The buyer matcher answers "who wants what I already made". A requirement board
answers the other direction, and the ranking reuses the same scoring rather
than a second, subtly different one — an artisan who sees two screens disagree
about which buyers suit them stops trusting both.

The quote sheet shows unit price × quantity, the pricing engine's cost, and the
resulting margin, because the failure mode for a first bulk order is accepting
it at a loss because the total looked large. Accepting a quote writes an
`Order` — the same rows the impact report counts, which is what makes those
figures transaction-derived instead of declared.

## Test isolation

The suite publishes listings, sends quotes and advances orders, so it mutates
the state it asserts against. It passed once and failed on the second run — the
worst kind of test, because the failure looks like a regression in whatever you
touched most recently. Two fixes: `main()` calls `POST /api/admin/reseed`
before anything else, and the sign-in check uses a random phone number per run
so "a new user is sent to onboarding" stays true. 118 checks now pass twice in
a row against the same running server, which is the property that actually
matters the morning of a demo.

## Things a reviewer should know are deliberate

- **SQLite, not Postgres.** One file, no service to start, trivially resettable
  before a demo. The SQLAlchemy layer moves to Postgres by changing one URL.
- **The search index is in memory and rebuilt on write.** At 16 listings this is
  free; past a few thousand it should move to SQLite FTS5 or Meilisearch. The
  `SearchIndex` class is the seam.
- **No CSS framework and no component library.** The design system is ~360 lines
  in `theme.css`. A craft marketplace that looks like every other Tailwind demo
  undersells the crafts.
- **Uploaded images are kept in a process-level cache plus disk.** Fine for a
  single-process demo; a multi-worker deployment needs object storage. The cache
  is confined to `routers/ai.py`.
- **Mobile-number sign-in has no SMS gateway.** The OTP is returned in the
  response and labelled on screen as a demo affordance. Wiring a provider is
  one function, `auth._deliver`. Pretending an SMS had been sent would have
  been the dishonest choice.
- **Government marketplace submission stops before the push.** Field mapping,
  HSN classification and the statutory declarations are complete; the POST
  needs a seller account granted to an organisation. The app states this
  rather than implying an integration.
- **The regional vocabulary is narrow on purpose.** Ten languages times a full
  dictionary would be unmaintainable and mostly unused. Ten languages times
  "the forty words that appear in a product description" is small, auditable
  and sufficient — and Indic scripts never collide, so the tables merge into
  one flat lookup with no ambiguity.
- **Accessibility is a scale factor, not a second stylesheet.** The in-app
  text-size control sets one `--font-scale` custom property on the root. The
  first version scaled only `html { font-size }`, which is the usual advice and
  was wrong here: this interface declares most of its type in explicit pixels,
  and a pixel does not care what the root font-size is — body copy grew while
  every button, label, chip and nav item stayed exactly where it was, so the
  control looked like it half-worked. Every declared size now carries the
  multiplier itself, `calc(Npx * var(--font-scale))`, in `theme.css` and in all
  329 inline sizes across the screens. Measured in a browser at 145%: root
  16→23.2px, buttons 15→21.75px, section titles 18→26.1px, with no horizontal
  overflow at 412px wide. High contrast is a `data-contrast` attribute that
  redefines the palette tokens, for the same reason — one switch, whole theme.
- **The service worker never caches writes.** A queued POST replaying later
  would publish a listing the artisan believed had failed. Reads fall back to
  the last good response and are tagged so the app can say "saved data"
  instead of presenting a stale price as live.
